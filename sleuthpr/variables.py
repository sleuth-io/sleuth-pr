from typing import Dict

from sleuthpr.models import ConditionVariableType
from sleuthpr.models import PullRequest


class NumberReviewersVariableType(ConditionVariableType):
    def __init__(self):
        super().__init__(
            key="number_reviewers",
            label="Number of reviewers",
            type=int,
            default_triggers=["pr_created", "pr_updated"],
        )

    def evaluate(self, context: Dict):
        pull_request: PullRequest = context["pull_request"]
        return len(pull_request.reviewers.all())
