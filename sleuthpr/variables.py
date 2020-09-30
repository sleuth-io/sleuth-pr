from typing import List

from sleuthpr.models import ConditionVariableType

NUMBER_REVIEWERS = ConditionVariableType(
    key="number_reviewers",
    label="Number of reviewers",
    type=int,
    default_triggers=["pr_created", "pr_updated"],
    evaluate=lambda context: len(context["pull_request"].reviewers.all()),
)

REVIEWER = ConditionVariableType(
    key="reviewer",
    label="Reviewer",
    type=List[str],
    default_triggers=["pr_created", "pr_updated"],
    evaluate=lambda context: [reviewer.user.username for reviewer in context["pull_request"].reviewers.all()],
)

NUMBER_ASSIGNEES = ConditionVariableType(
    key="number_assignees",
    label="Number of assignees",
    type=int,
    default_triggers=["pr_created", "pr_updated"],
    evaluate=lambda context: len(context["pull_request"].assignees.all()),
)

ASSIGNEE = ConditionVariableType(
    key="assignee",
    label="Assignee",
    type=List[str],
    default_triggers=["pr_created", "pr_updated"],
    evaluate=lambda context: [assignee.user.username for assignee in context["pull_request"].assignees.all()],
)


LABEL = ConditionVariableType(
    key="label",
    label="Label",
    type=List[str],
    default_triggers=["pr_created", "pr_updated"],
    evaluate=lambda context: [label.value for label in context["pull_request"].labels.all()],
)


MERGEABLE = ConditionVariableType(
    key="mergeable",
    label="Mergeable",
    type=bool,
    default_triggers=["pr_created", "pr_updated", "pr_closed"],
    evaluate=lambda context: context["pull_request"].mergeable,
)


MERGED = ConditionVariableType(
    key="merged",
    label="Merged",
    type=bool,
    default_triggers=["pr_closed"],
    evaluate=lambda context: context["pull_request"].merged,
)
