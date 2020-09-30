import logging

from sleuthpr.models import Installation
from sleuthpr.models import PullRequest
from sleuthpr.models import Repository
from sleuthpr.services import checks
from sleuthpr.services import rules
from sleuthpr.triggers import PR_CREATED
from sleuthpr.triggers import PR_UPDATED

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
