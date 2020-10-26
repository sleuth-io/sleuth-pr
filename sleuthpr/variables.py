import logging
from functools import partial
from typing import List

from sleuthpr.models import CheckStatus
from sleuthpr.models import ConditionVariableType
from sleuthpr.models import PullRequest
from sleuthpr.models import ReviewState
from sleuthpr.models import TriState
from sleuthpr.triggers import BASE_BRANCH_UPDATED
from sleuthpr.triggers import PR_CLOSED
from sleuthpr.triggers import PR_CREATED
from sleuthpr.triggers import PR_REOPENED
from sleuthpr.triggers import PR_UPDATED
from sleuthpr.triggers import REVIEW_UPDATED
from sleuthpr.triggers import STATUS_UPDATED


logger = logging.getLogger(__name__)


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

AUTHOR = ConditionVariableType(
    key="author",
    label="Pull request and commit authors",
    type=List[str],
    default_triggers=[PR_CREATED, PR_UPDATED],
    evaluate=lambda context: [context["pull_request"].author.username]
    + [c.author.username for c in context["pull_request"].commits if c.author],
)

TITLE = ConditionVariableType(
    key="title",
    label="Pull request title",
    type=str,
    default_triggers=[PR_CREATED, PR_UPDATED],
    evaluate=lambda context: context["pull_request"].title,
)

DESCRIPTION = ConditionVariableType(
    key="description",
    label="Pull request description",
    type=str,
    default_triggers=[PR_CREATED, PR_UPDATED],
    evaluate=lambda context: context["pull_request"].description,
)

PULL_REQUEST_AUTHOR = ConditionVariableType(
    key="pull_request_author",
    label="Pull request author",
    type=str,
    default_triggers=[PR_CREATED, PR_UPDATED],
    evaluate=lambda context: context["pull_request"].author.username,
)

COMMIT_AUTHOR = ConditionVariableType(
    key="commit_author",
    label="Authors of commits in the pull request",
    type=List[str],
    default_triggers=[PR_CREATED, PR_UPDATED],
    evaluate=lambda context: [c.author.username for c in context["pull_request"].commits if c.author],
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
    evaluate=lambda context: TriState(context["pull_request"].mergeable).to_bool(),
)

MERGED = ConditionVariableType(
    key="merged",
    label="Merged",
    type=bool,
    default_triggers=[PR_CLOSED],
    evaluate=lambda context: context["pull_request"].merged,
)


DRAFT = ConditionVariableType(
    key="draft",
    label="Draft",
    type=bool,
    default_triggers=[PR_CREATED, PR_UPDATED, PR_CLOSED],
    evaluate=lambda context: context["pull_request"].draft,
)


CLOSED = ConditionVariableType(
    key="closed",
    label="Closed",
    type=bool,
    default_triggers=[PR_CLOSED, PR_REOPENED],
    evaluate=lambda context: context["pull_request"].merged,
)

BASE = ConditionVariableType(
    key="base",
    label="Base branch",
    type=str,
    default_triggers=[PR_CREATED, PR_UPDATED],
    evaluate=lambda context: context["pull_request"].base_branch_name,
)

CONFLICT = ConditionVariableType(
    key="conflict",
    label="Conflict with base branch",
    type=bool,
    default_triggers=[BASE_BRANCH_UPDATED, PR_UPDATED, PR_CREATED],
    evaluate=lambda context: TriState(context["pull_request"].conflict).to_bool(),
)

COMMIT_MESSAGE = ConditionVariableType(
    key="commit_message",
    label="Commit messages",
    type=List[str],
    default_triggers=[PR_CREATED, PR_UPDATED],
    evaluate=lambda context: [commit.message for commit in context["pull_request"].commits],
)


def _is_base_branch_synchronized(pull_request: PullRequest):
    repo = pull_request.repository

    branch_head = repo.branches.filter(name=pull_request.base_branch_name).first()
    if branch_head:
        branch_head.refresh_from_db()
        logger.info(f"Branch {branch_head.name} and head {branch_head.head_sha} for pr {pull_request.remote_id}")
        result = repo.commit_tree.filter(child__pull_request=pull_request, parent__sha=branch_head.head_sha).exists()
        if not result:
            logger.info(
                f"Nothing in the tree where the parent ({branch_head.name}) "
                f"is {branch_head.head_sha} and has a pull request"
            )
            without_pr = repo.commit_tree.filter(parent__sha=branch_head.head_sha).first()
            logger.info(
                f"Does that sha exist but just not associated with the pull request? "
                f"{without_pr.child.sha if without_pr else 'No'}"
                f" and {without_pr.child.pull_request if without_pr else 'No'} and "
                f"{without_pr.child.id if without_pr else 'No'}"
            )
        return result
    else:
        logger.info(f"No base head found for {pull_request.base_branch_name}")
        return False


BEHIND = ConditionVariableType(
    key="behind",
    label="Pull request is behind the base branch",
    type=bool,
    default_triggers=[PR_CREATED, PR_UPDATED],
    evaluate=lambda context: not _is_base_branch_synchronized(context["pull_request"]),
)


def _get_context_list(context, status):
    return [item.context for item in context["pull_request"].statuses.filter(state=status).all()]


STATUS_STATE_VARS = [
    ConditionVariableType(
        key=f"status_{status}",
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
        key=f"review_{status}",
        label=f"List of usernames that have reviewed the PR in a {label} state",
        type=list,
        default_triggers=[REVIEW_UPDATED],
        evaluate=partial(_get_username_list, status=status),  # noqa
    )
    for status, label in ReviewState.choices
]
