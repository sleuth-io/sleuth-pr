import logging
from typing import Dict
from typing import Tuple

from dateutil import parser
from django.db import transaction

from sleuthpr.models import CheckStatus
from sleuthpr.models import ExternalUser
from sleuthpr.models import Installation
from sleuthpr.models import PullRequest
from sleuthpr.models import PullRequestAssignee
from sleuthpr.models import PullRequestLabel
from sleuthpr.models import PullRequestReviewer
from sleuthpr.models import Repository
from sleuthpr.models import RepositoryIdentifier
from sleuthpr.models import ReviewState
from sleuthpr.models import TriState
from sleuthpr.services import branches
from sleuthpr.services import checks
from sleuthpr.services import external_users
from sleuthpr.services import installations
from sleuthpr.services import pull_requests
from sleuthpr.services import repositories
from sleuthpr.services import rules
from sleuthpr.services.scm import Commit
from sleuthpr.triggers import PR_CLOSED
from sleuthpr.triggers import PR_CREATED
from sleuthpr.triggers import PR_REOPENED
from sleuthpr.triggers import PR_UPDATED
from sleuthpr.util import dirty_set_all

logger = logging.getLogger(__name__)


def on_check_suite_requested(installation: Installation, repository: Repository, data: Dict):
    for pr_data in data["pull_requests"]:
        pr, was_changed = _update_pull_request(installation, repository, pr_data)
        checks.clear_checks(pr)
        if was_changed:
            pull_requests.on_updated(installation, repository, pr)


def on_pull_request_review(installation: Installation, repository: Repository, data: Dict):
    pr_data = data["pull_request"]
    pr, was_changed = _update_pull_request(installation, repository, pr_data)
    if was_changed:
        pull_requests.on_updated(installation, repository, pr)

    reviewer = (_get_user(installation, data["review"]["user"]),)
    pull_requests.update_review(installation, repository, pr, reviewer, ReviewState(data["action"].lower()))


def on_status(installation: Installation, repository: Repository, data: Dict):
    context = data["context"]
    state = CheckStatus(data["state"])
    sha = data["commit"]["sha"]
    pull_requests.update_status(installation, repository, context=context, state=state, sha=sha)


def on_check_run(installation: Installation, repository: Repository, data: Dict):
    for pr_data in data["pull_requests"]:
        _update_pull_request_and_process(installation, repository, pr_data)


def on_push(installation: Installation, repository: Repository, data: Dict):
    pull_requests.add_commits(
        repository,
        [
            Commit(
                sha=c.get("id", c.get("sha")),
                message=c["message"],
                parents=[],
                author_name=c["author"]["name"],
                author_email=c["author"]["name"],
                committer_name=c["committer"]["name"],
                committer_email=c["committer"]["email"],
            )
            for c in data["commits"]
        ],
    )
    if "refs/heads/master" == data["ref"]:
        files = {}
        for commit in data["commits"]:
            for action in ("modified", "added", "removed"):
                for file in commit.get(action, []):
                    files[file] = action

        if files.get(".sleuth/rules.yml"):
            logger.info("Push contained a rules file change, refreshing")
            rules.refresh(installation, repository)

        logger.info("Got a master push")
    else:
        logger.info("Not a master push")

    if data["ref"].startswith("refs/heads/"):
        branch_name = data["ref"][len("refs/heads/") :]
        logger.info(f"Detected a head push for {branch_name}")
        sha = data["after"]
        branches.update_sha(installation, repository, branch_name, sha)


def on_pr_created(installation: Installation, repository: Repository, pr_data: Dict):
    pr = _update_pull_request_and_process(installation, repository, pr_data, event=PR_CREATED)
    pull_requests.refresh_commits(installation, repository, pr)


def on_pr_updated(installation: Installation, repository: Repository, pr_data: Dict):
    pr = _update_pull_request_and_process(installation, repository, pr_data)
    pull_requests.refresh_commits(installation, repository, pr)


def on_pr_closed(installation: Installation, repository: Repository, pr_data: Dict):
    _update_pull_request_and_process(installation, repository, pr_data, event=PR_CLOSED)


def on_pr_reopened(installation: Installation, repository: Repository, pr_data: Dict):
    _update_pull_request_and_process(installation, repository, pr_data, event=PR_REOPENED)


def on_repositories_added(installation: Installation, data):
    if data["repository_selection"] == "all":
        repos = installation.client.get_repositories()
        repositories.set_repositories(installation, repos)
    else:
        repos = [
            RepositoryIdentifier(full_name=repo["full_name"], remote_id=repo["id"])
            for repo in data["repositories_added"]
        ]
        repositories.add(installation, repos)


def on_repositories_removed(installation: Installation, data):
    if data["repository_selection"] == "all":
        repos = installation.client.get_repositories()
        repositories.set_repositories(installation, repos)
    else:
        repos = [
            RepositoryIdentifier(full_name=repo["full_name"], remote_id=repo["id"])
            for repo in data["repositories_removed"]
        ]
        repositories.remove(installation, repos)


def on_installation_created(remote_id: str, data):
    target_type = data["installation"]["target_type"]
    target_id = data["installation"]["target_id"]
    repos = [RepositoryIdentifier(full_name=repo["full_name"], remote_id=repo["id"]) for repo in data["repositories"]]
    installations.create(
        remote_id=remote_id,
        target_type=target_type,
        target_id=target_id,
        repository_ids=repos,
        provider="github",
    )


def _update_pull_request_and_process(
    installation: Installation, repository: Repository, data: Dict, event=PR_UPDATED
):
    pr, _ = _update_pull_request(installation, repository, data)
    if event == PR_CREATED:
        pull_requests.on_created(installation, repository, pr)
    else:
        pull_requests.on_updated(installation, repository, pr)
    return pr


@transaction.atomic
def _update_pull_request(installation: Installation, repository: Repository, data: Dict) -> Tuple[PullRequest, bool]:
    remote_id = data["number"]

    pr: PullRequest = repository.pull_requests.filter(remote_id=remote_id).first()
    if not pr:
        pr = PullRequest(repository=repository)

    is_dirty = _update_pr_headers(data, pr, remote_id)

    if is_dirty:
        pr.save()

    if "title" not in data:
        return pr, is_dirty

    is_dirty = _update_pr_details(data, installation, pr) | is_dirty

    if is_dirty:
        pr.save()

    assignees = set()
    for assignee_data in data.get("assignees", []):
        assignees.add(_get_user(installation, assignee_data))
    existing_assignees = {person.user.remote_id for person in pr.assignees.all()}
    if {str(person.remote_id) for person in assignees} != existing_assignees:
        pr.assignees.all().delete()
        for assignee_data in data.get("assignees", []):
            person = _get_user(installation, assignee_data)
            PullRequestAssignee.objects.create(user=person, pull_request=pr)
        is_dirty = True
        logger.info(f"DIRTY!!!!! assignees old {existing_assignees} new {assignees}")

    reviewers = set()
    for reviewer_data in data.get("requested_reviewers", []):
        reviewers.add(_get_user(installation, reviewer_data))
    existing_reviewers = {person.user.remote_id for person in pr.reviewers.all()}
    if {str(reviewer.remote_id) for reviewer in reviewers} != existing_reviewers:
        pr.reviewers.all().delete()
        for reviewer in reviewers:
            PullRequestReviewer.objects.create(user=reviewer, pull_request=pr)
        is_dirty = True
        logger.info(f"DIRTY!!!!! reviewers old {existing_reviewers} new {reviewers}")

    existing_labels = {label.value for label in pr.labels.all()}
    labels = {label_data["name"] for label_data in data.get("labels", [])}
    if labels != existing_labels:
        pr.labels.all().delete()
        for label_name in labels:
            PullRequestLabel.objects.create(pull_request=pr, value=label_name)
        logger.info(f"DIRTY!!!!! labels old {existing_labels} new {labels}")
        is_dirty = True

    return pr, is_dirty


def _update_pr_details(data, installation, pr):
    return dirty_set_all(
        pr,
        dict(
            title=data["title"],
            description=data.get("body"),
            url=data["html_url"],
            on=parser.parse(data["created_at"]),
            author=_get_user(installation, data["user"]),
            draft=data["draft"],
            merged=data.get("merged", False),
            conflict=TriState.UNKNOWN.value
            if not data.get("mergeable_state")
            else TriState.from_bool(data.get("mergeable_state") == "dirty").value,
            mergeable=TriState.from_bool(data.get("mergeable")).value,
            rebaseable=TriState.from_bool(data.get("rebaseable")).value,
        ),
    )


def _update_pr_headers(data, pr, remote_id):
    return dirty_set_all(
        pr,
        dict(
            remote_id=str(remote_id),
            source_branch_name=data["head"]["ref"],
            source_sha=data["head"]["sha"],
            base_branch_name=data["base"]["ref"],
            base_sha=data["head"]["sha"],
        ),
    )


def _get_user(installation: Installation, data: Dict) -> ExternalUser:
    return external_users.get_or_create(
        installation=installation,
        username=data.get("login"),
        remote_id=data.get("id"),
        email=data.get("email"),
        name=data.get("name"),
    )
