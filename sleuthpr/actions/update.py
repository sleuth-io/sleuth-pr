import logging
from typing import Dict
from typing import Tuple

from marshmallow import Schema

from sleuthpr.models import Action
from sleuthpr.models import ActionType
from sleuthpr.models import CheckStatus
from sleuthpr.models import PullRequest
from sleuthpr.services.scm import OperationException


logger = logging.getLogger(__name__)


class UpdatePullRequestBaseActionType(ActionType):
    def __init__(self):
        super().__init__(
            key="update_pull_request_base",
            label="Update the pull request from the base branch",
            parameters=UpdatePullRequestBaseActionSchema(),
            conditions=[
                "merged=false",
            ],
        )

    def execute(self, action: Action, context: Dict) -> Tuple[CheckStatus, str]:
        pull_request: PullRequest = context["pull_request"]
        if pull_request.merged:
            logger.info("PR already merged, skipping update")
            return CheckStatus.SUCCESS, "Pull request already up to date, skipping update"
        try:
            action.rule.repository.installation.client.update_pull_request(
                pull_request.repository,
                int(pull_request.remote_id),
                sha=pull_request.source_sha,
            )
            return CheckStatus.PENDING, f"Updating the pull request by merging base"
        except OperationException as ex:
            return CheckStatus.ERROR, f"Unable to update pull request by merging master: {ex}"


class UpdatePullRequestBaseActionSchema(Schema):
    pass
