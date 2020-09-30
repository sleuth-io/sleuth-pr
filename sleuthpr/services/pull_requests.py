import logging

from django.db.models import Q

from sleuthpr.models import CheckStatus
from sleuthpr.models import ExternalUser
from sleuthpr.models import Installation
from sleuthpr.models import PullRequest
from sleuthpr.models import PullRequestReviewer
from sleuthpr.models import PullRequestStatus
from sleuthpr.models import Repository
from sleuthpr.models import ReviewState
from sleuthpr.services import checks
from sleuthpr.services import rules
from sleuthpr.triggers import BASE_BRANCH_UPDATED
from sleuthpr.triggers import PR_CREATED
from sleuthpr.triggers import PR_UPDATED
from sleuthpr.triggers import REVIEW_UPDATED
from sleuthpr.triggers import STATUS_UPDATED
from sleuthpr.util import dirty_set_all

logger = logging.getLogger(__name__)


def on_updated(installation: Installation, repository: Repository, pull_request: PullRequest):
    logger.info(f"Updated pull request: {pull_request.remote_id} on {repository.full_name}")
    checks.update_checks(installation, repository, pull_request)
    rules.evaluate(repository, PR_UPDATED, {"pull_request": pull_request})


def on_created(installation: Installation, repository: Repository, pull_request: PullRequest):
    logger.info(f"Created pull request: {pull_request.remote_id} on {repository.full_name}")
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

        checks.update_checks(installation, repository, pull_request)
        rules.evaluate(repository, PR_CREATED, {"pull_request": pull_request})
