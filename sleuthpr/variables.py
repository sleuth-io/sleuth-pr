from functools import partial
from typing import List

from sleuthpr.models import CheckStatus
from sleuthpr.models import ConditionVariableType
from sleuthpr.models import PullRequest
from sleuthpr.models import ReviewState
from sleuthpr.triggers import PR_CLOSED
from sleuthpr.triggers import PR_CREATED
from sleuthpr.triggers import PR_UPDATED
from sleuthpr.triggers import REVIEW_UPDATED
from sleuthpr.triggers import STATUS_UPDATED

NUMBER_REVIEWERS = ConditionVariableType(
    key="number_reviewers",
    label="Number of reviewers",
    type=int,
    default_triggers=[PR_CREATED, PR_UPDATED],
    evaluate=lambda context: len(context["pull_request"].reviewers.all()),
)

REVIEWER = ConditionVariableType(
    key="reviewer",
    label="Reviewer",
    type=List[str],
    default_triggers=[PR_CREATED, PR_UPDATED],
    evaluate=lambda context: [reviewer.user.username for reviewer in context["pull_request"].reviewers.all()],
)

NUMBER_ASSIGNEES = ConditionVariableType(
    key="number_assignees",
    label="Number of assignees",
    type=int,
    default_triggers=[PR_CREATED, PR_UPDATED],
    evaluate=lambda context: len(context["pull_request"].assignees.all()),
)

ASSIGNEE = ConditionVariableType(
    key="assignee",
    label="Assignee",
    type=List[str],
    default_triggers=[PR_CREATED, PR_UPDATED],
    evaluate=lambda context: [assignee.user.username for assignee in context["pull_request"].assignees.all()],
)

LABEL = ConditionVariableType(
    key="label",
    label="Label",
    type=List[str],
    default_triggers=[PR_CREATED, PR_UPDATED],
    evaluate=lambda context: [label.value for label in context["pull_request"].labels.all()],
)

MERGEABLE = ConditionVariableType(
    key="mergeable",
    label="Mergeable",
    type=bool,
    default_triggers=[PR_CREATED, PR_UPDATED, PR_CLOSED],
    evaluate=lambda context: context["pull_request"].mergeable,
)

MERGED = ConditionVariableType(
    key="merged",
    label="Merged",
    type=bool,
    default_triggers=[PR_CLOSED],
    evaluate=lambda context: context["pull_request"].merged,
)


def _is_base_branch_synchronized(pull_request: PullRequest):
    repo = pull_request.repository

    branch_head = repo.branches.filter(name=pull_request.base_branch_name).first()
    return repo.commit_tree.filter(child__pull_request=pull_request, parent__sha=branch_head.head_sha).exists()


BASE_SYNCED = ConditionVariableType(
    key="base_synced",
    label="Base branch synchronized",
    type=bool,
    default_triggers=[PR_CREATED, PR_UPDATED],
    evaluate=lambda context: _is_base_branch_synchronized(context["pull_request"]),
)


def _get_context_list(context, status):
    return [item.context for item in context["pull_request"].statuses.filter(state=status).all()]


STATUS_STATE_VARS = [
    ConditionVariableType(
        key=f"status-{status}",
        label=f"List of status contexts in a {label} state",
        type=list,
        default_triggers=[STATUS_UPDATED],
        evaluate=partial(_get_context_list, status=status),  # noqa
    )
    for status, label in CheckStatus.choices
]


def _get_username_list(context, status):
    return [item.user.username for item in context["pull_request"].reviewers.filter(state=status).all()]


REVIEW_STATE_VARS = [
    ConditionVariableType(
        key=f"review-{status}",
        label=f"List of usernames that have reviewed the PR in a {label} state",
        type=list,
        default_triggers=[REVIEW_UPDATED],
        evaluate=partial(_get_username_list, status=status),  # noqa
    )
    for status, label in ReviewState.choices
]
