from typing import Any
from typing import Dict

from marshmallow import fields
from marshmallow import Schema

from sleuthpr.models import Action
from sleuthpr.models import ActionType
from sleuthpr.models import ConditionVariableType
from sleuthpr.models import TriggerType

PR_UPDATED = TriggerType("pr_updated", "Pull request updated")
PR_CREATED = TriggerType("pr_created", "Pull request created")

trigger_types = [PR_UPDATED, PR_CREATED]


class NumberReviewersVariableType(ConditionVariableType):
    def __init__(self):
        super().__init__(
            key="number_reviewers",
            label="Number of reviewers",
            type=int,
            default_triggers=["pr_created", "pr_updated"],
        )

    def evaluate(self, target: Any):
        return len(target.reviewers)


condition_variable_types = [NumberReviewersVariableType()]


class AddLabelActionSchema(Schema):
    value = fields.Str(description="The label name to add")


class AddLabelActionType(ActionType):
    def __init__(self):
        super().__init__(
            "add_label", "Add a label to the pull request", AddLabelActionSchema()
        )

    def execute(self, action: Action, target: Any):
        label_name = action.parameters["value"]
        action.rule.repository.installation.client.add_label(
            action.rule.repository.identifier, target["number"], label_name
        )


action_types = [AddLabelActionType()]
