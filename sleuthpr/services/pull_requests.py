import logging
from typing import Dict
from typing import List
from typing import Set
from typing import Tuple

from django.db import transaction
from django.db.models import Q

from sleuthpr.models import CheckStatus
from sleuthpr.models import ExternalUser
from sleuthpr.models import Installation
from sleuthpr.models import PullRequest
from sleuthpr.models import PullRequestReviewer
from sleuthpr.models import PullRequestStatus
from sleuthpr.models import Repository
from sleuthpr.models import RepositoryCommit
from sleuthpr.models import RepositoryCommitParent
from sleuthpr.models import ReviewState
from sleuthpr.services import checks
from sleuthpr.services import external_users
from sleuthpr.services import rules
from sleuthpr.services.scm import Commit
from sleuthpr.triggers import BASE_BRANCH_UPDATED
from sleuthpr.triggers import PR_CREATED
from sleuthpr.triggers import PR_UPDATED
from sleuthpr.triggers import REVIEW_UPDATED
from sleuthpr.triggers import STATUS_UPDATED
from sleuthpr.util import dirty_set_all

logger = logging.getLogger(__name__)


def on_updated(installation: Installation, repository: Repository, pull_request: PullRequest):
    logger.info(f"Updated pull request: {pull_request.remote_id} on {repository.full_name}")

    # refresh files and commits
    refresh_commits(installation, repository, pull_request)

    checks.update_checks(installation, repository, pull_request)
    rules.evaluate(repository, PR_UPDATED, {"pull_request": pull_request})


def on_created(installation: Installation, repository: Repository, pull_request: PullRequest):
    logger.info(f"Created pull request: {pull_request.remote_id} on {repository.full_name}")
    # refresh files and commits

    refresh_commits(installation, repository, pull_request)
    checks.update_checks(installation, repository, pull_request)
    rules.evaluate(repository, PR_CREATED, {"pull_request": pull_request})


def delete(repository: Repository, pull_request: PullRequest):
    pull_request.delete()
    logger.info(f"Created pull request: {pull_request.remote_id} on {repository.full_name}")


def update_status(installation: Installation, repository: Repository, context: str, state: CheckStatus, sha: str):
    for pr in repository.pull_requests.filter(source_sha=sha).all():  # type: PullRequest
        status = pr.statuses.filter(context=context).first()
        if status:
            dirty = dirty_set_all(status, dict(state=str(state)))
        else:
            status = PullRequestStatus.objects.create(pull_request=pr, context=context, state=state)
            dirty = True
        if dirty:
            logger.info(
                f"Updated check {status.context} to {status.state} for pull request: {pr.remote_id} "
                f"on {repository.full_name}"
            )
            checks.update_checks(installation, repository, pr)
            rules.evaluate(repository, STATUS_UPDATED, {"pull_request": pr, "status": status})


def update_review(
    installation: Installation,
    repository: Repository,
    pull_request: PullRequest,
    reviewer: ExternalUser,
    state: ReviewState,
):
    review: PullRequestReviewer = pull_request.reviewers.filter(user=reviewer).first()
    if review:
        dirty = dirty_set_all(review, dict(state=state))
        if dirty:
            logger.info(
                f"Updated review {reviewer.remote_id} to {state} for pull request: {pull_request.remote_id} "
                f"on {repository.full_name}"
            )
            checks.update_checks(installation, repository, pull_request)
            rules.evaluate(repository, REVIEW_UPDATED, {"pull_request": pull_request, "reviewer": review})
    else:
        logger.error(f"Missing existing pr reviewer for user {reviewer.id} on pr {pull_request.id}")


def on_source_change(installation: Installation, repository: Repository, name: str, sha: str):
    for pull_request in (
        repository.pull_requests.filter(base_branch_name=name).filter(~Q(base_sha=sha)).all()
    ):  # type: PullRequest
        logger.info(
            f"PR's base branch updated, updating pull request: {pull_request.remote_id} " f"on {repository.full_name}"
        )
        checks.update_checks(installation, repository, pull_request)
        rules.evaluate(repository, BASE_BRANCH_UPDATED, {"pull_request": pull_request})


def refresh(installation: Installation, repository: Repository):
    for pull_request in installation.client.get_pull_requests(repository):
        for context, state in installation.client.get_statuses(repository.identifier, pull_request.source_sha):
            status = PullRequestStatus.objects.create(pull_request=pull_request, context=context, state=state)
            rules.evaluate(repository, STATUS_UPDATED, {"pull_request": pull_request, "status": status})

        refresh_commits(installation, repository, pull_request)

        checks.update_checks(installation, repository, pull_request)
        rules.evaluate(repository, PR_CREATED, {"pull_request": pull_request})


def refresh_commits(installation: Installation, repository: Repository, pull_request: PullRequest):
    all_commits: List[Commit] = []
    for commit in installation.client.get_pull_request_commits(repository.identifier, int(pull_request.remote_id)):
        all_commits.append(commit)

    RepositoryCommit.objects.filter(pull_request=pull_request).update(pull_request=None)
    chunk_size = 100
    chunks: List[List[Commit]] = [all_commits[i : i + chunk_size] for i in range(0, len(all_commits), chunk_size)]
    for chunk in chunks:
        changed_shas = add_commits(repository, chunk)
        RepositoryCommit.objects.filter(sha__in=[sha for sha in changed_shas]).update(pull_request=pull_request)


@transaction.atomic
def add_commits(repository: Repository, commits: List[Commit]) -> Set[str]:
    changed_shas = set()

    links: List[Tuple] = []
    all_shas: List[str] = []
    for commit in commits:
        for parent in commit.parents:
            links.append((commit.sha, parent))
            all_shas.append(commit.sha)
            all_shas.append(parent)

    commits_by_child: Dict[str, Commit] = {c.sha: c for c in commits}

    # Find existing RepositoryCommits for both children and parents
    repo_commits = {c.sha: c for c in repository.commits.filter(sha__in=all_shas).all()}

    # Add any missing RepositoryCommits
    for sha in [s for s in all_shas if s not in repo_commits]:
        commit = commits_by_child.get(sha, None)
        if commit:
            author = external_users.get_or_create(
                installation=repository.installation, name=commit.author_name, email=commit.author_email
            )
            committer = external_users.get_or_create(
                installation=repository.installation, name=commit.author_name, email=commit.author_email
            )
            message = commit.message
        else:
            message = author = committer = None

        repo_commit = RepositoryCommit.objects.create(
            repository=repository, sha=sha, message=message, author=author, committer=committer
        )
        repo_commits[repo_commit.sha] = repo_commit
        changed_shas.add(sha)

    # Find existing RepositoryCommitParents
    saved_link_shas = {
        f"{c.child.sha}:{c.parent.sha}": c
        for c in repository.commit_tree.select_related("child", "parent")
        .filter(child__sha__in=[child for child, _ in links])
        .all()
    }

    # Add any missing RepositoryCommitParents
    for child_sha, parent_sha in [link for link in links if not saved_link_shas.get(":".join(link))]:
        RepositoryCommitParent.objects.create(
            repository=repository, parent=repo_commits[parent_sha], child=repo_commits[child_sha]
        )
        changed_shas.add(child_sha)

    logger.info(f"Updated {len(changed_shas)} changed shas in the db")
    return changed_shas
