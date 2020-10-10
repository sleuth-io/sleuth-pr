from sleuthpr.actions.add_label import AddPullRequestLabelActionType
from sleuthpr.actions.merge import MergePullRequestActionType
from sleuthpr.actions.update import UpdatePullRequestBaseActionType
from sleuthpr.triggers import BASE_BRANCH_UPDATED
from sleuthpr.triggers import PR_CLOSED
from sleuthpr.triggers import PR_CREATED
from sleuthpr.triggers import PR_REOPENED
from sleuthpr.triggers import PR_UPDATED
from sleuthpr.triggers import REVIEW_UPDATED
from sleuthpr.triggers import STATUS_UPDATED
from sleuthpr.variables import ASSIGNEE
from sleuthpr.variables import AUTHOR
from sleuthpr.variables import BASE
from sleuthpr.variables import BEHIND
from sleuthpr.variables import CLOSED
from sleuthpr.variables import COMMIT_AUTHOR
from sleuthpr.variables import COMMIT_MESSAGE
from sleuthpr.variables import CONFLICT
from sleuthpr.variables import DESCRIPTION
from sleuthpr.variables import DRAFT
from sleuthpr.variables import LABEL
from sleuthpr.variables import MERGEABLE
from sleuthpr.variables import MERGED
from sleuthpr.variables import NUMBER_ASSIGNEES
from sleuthpr.variables import NUMBER_REVIEWERS
from sleuthpr.variables import PULL_REQUEST_AUTHOR
from sleuthpr.variables import REVIEW_STATE_VARS
from sleuthpr.variables import REVIEWER
from sleuthpr.variables import STATUS_STATE_VARS
from sleuthpr.variables import TITLE

trigger_types = [PR_UPDATED, PR_CREATED, PR_CLOSED, STATUS_UPDATED, REVIEW_UPDATED, BASE_BRANCH_UPDATED, PR_REOPENED]

condition_variable_types = [
    NUMBER_REVIEWERS,
    REVIEWER,
    NUMBER_ASSIGNEES,
    ASSIGNEE,
    LABEL,
    MERGED,
    MERGEABLE,
    BEHIND,
    CONFLICT,
    DRAFT,
    CLOSED,
    BASE,
    COMMIT_MESSAGE,
    AUTHOR,
    PULL_REQUEST_AUTHOR,
    COMMIT_AUTHOR,
    TITLE,
    DESCRIPTION,
    *STATUS_STATE_VARS,
    *REVIEW_STATE_VARS,
]

action_types = [AddPullRequestLabelActionType(), MergePullRequestActionType(), UpdatePullRequestBaseActionType()]
