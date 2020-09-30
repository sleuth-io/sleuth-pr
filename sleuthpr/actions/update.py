from typing import Dict

from marshmallow import Schema

from sleuthpr.models import Action
from sleuthpr.models import ActionType
from sleuthpr.models import PullRequest


class UpdatePullRequestBaseActionType(ActionType):
    def __init__(self):
        super().__init__(
            "update_pull_request_base",
            "Update the pull request from the base branch",
            UpdatePullRequestBaseActionSchema(),
        )

    def execute(self, action: Action, context: Dict):
        pull_request: PullRequest = context["pull_request"]

        action.rule.repository.installation.client.update_pull_request(
            pull_request.repository.identifier,
            int(pull_request.remote_id),
            sha=pull_request.source_sha,
        )
        action.rule.repository.installation.client.comment_on_pull_request(
            pull_request.repository.identifier,
            int(pull_request.remote_id),
            pull_request.source_sha,
            message=f"Updated the pull request by merging master as requested by rule {action.rule.title}",
        )


class UpdatePullRequestBaseActionSchema(Schema):
    pass
