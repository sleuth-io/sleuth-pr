from typing import Dict

from marshmallow import Schema

from sleuthpr.models import Action
from sleuthpr.models import ActionType
from sleuthpr.models import PullRequest
from sleuthpr.services.scm import OperationException


class UpdatePullRequestBaseActionType(ActionType):
    def __init__(self):
        super().__init__(
            "update_pull_request_base",
            "Update the pull request from the base branch",
            UpdatePullRequestBaseActionSchema(),
        )

    def execute(self, action: Action, context: Dict):
        pull_request: PullRequest = context["pull_request"]

        try:
            action.rule.repository.installation.client.update_pull_request(
                pull_request.repository.identifier,
                int(pull_request.remote_id),
                sha=pull_request.source_sha,
            )
            message = f"Updated the pull request by merging master as requested by rule {action.rule.title}"
        except OperationException as ex:
            message = f"Unable to update pull request by merging master as requested by rule {action.rule.title}: {ex}"

        action.rule.repository.installation.client.comment_on_pull_request(
            pull_request.repository.identifier,
            int(pull_request.remote_id),
            pull_request.source_sha,
            message=message,
        )


class UpdatePullRequestBaseActionSchema(Schema):
    pass
