import logging
from typing import Dict

from marshmallow import Schema

from sleuthpr.models import Action
from sleuthpr.models import ActionType
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

    def execute(self, action: Action, context: Dict):
        pull_request: PullRequest = context["pull_request"]
        if pull_request.merged:
            logger.info("PR already merged, skipping update")
            return False
        try:
            action.rule.repository.installation.client.update_pull_request(
                pull_request.repository.identifier,
                int(pull_request.remote_id),
                sha=pull_request.source_sha,
            )
            message = f"Updated the pull request by merging master as requested by rule {action.rule.title}"
        except OperationException as ex:
            message = (
                f"Unable to update pull request by merging master as requested by rule {action.rule.title}: {ex}"
            )

        action.rule.repository.installation.client.comment_on_pull_request(
            pull_request.repository.identifier,
            int(pull_request.remote_id),
            pull_request.source_sha,
            message=message,
        )

        return True


class UpdatePullRequestBaseActionSchema(Schema):
    pass
