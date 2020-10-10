from typing import Dict
from typing import Tuple

from marshmallow import fields
from marshmallow import Schema

from sleuthpr.models import Action
from sleuthpr.models import ActionType
from sleuthpr.models import CheckStatus
from sleuthpr.models import PullRequest


class AddPullRequestLabelActionType(ActionType):
    def __init__(self):
        super().__init__(
            "add_pull_request_label", "Add a label to the pull request", AddPullRequestLabelActionSchema()
        )

    def execute(self, action: Action, context: Dict) -> Tuple[CheckStatus, str]:
        pull_request: PullRequest = context["pull_request"]
        label_name = action.parameters["value"]
        action.rule.repository.installation.client.add_label(
            action.rule.repository.identifier, int(pull_request.remote_id), label_name
        )
        return CheckStatus.SUCCESS, "Label {label_name} added"


class AddPullRequestLabelActionSchema(Schema):
    value = fields.Str(description="The label name to add")
