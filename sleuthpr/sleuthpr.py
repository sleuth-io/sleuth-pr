from sleuthpr.actions.add_label import AddPullRequestLabelActionType
from sleuthpr.actions.merge import MergePullRequestActionType
from sleuthpr.actions.update import UpdatePullRequestBaseActionType
from sleuthpr.triggers import BASE_BRANCH_UPDATED
from sleuthpr.triggers import PR_CLOSED
from sleuthpr.triggers import PR_CREATED
from sleuthpr.triggers import PR_UPDATED
from sleuthpr.triggers import REVIEW_UPDATED
from sleuthpr.triggers import STATUS_UPDATED
from sleuthpr.variables import ASSIGNEE
from sleuthpr.variables import BASE_SYNCED
from sleuthpr.variables import LABEL
from sleuthpr.variables import MERGEABLE
from sleuthpr.variables import MERGED
from sleuthpr.variables import NUMBER_ASSIGNEES
from sleuthpr.variables import NUMBER_REVIEWERS
from sleuthpr.variables import REVIEW_STATE_VARS
from sleuthpr.variables import REVIEWER
from sleuthpr.variables import STATUS_STATE_VARS

trigger_types = [PR_UPDATED, PR_CREATED, PR_CLOSED, STATUS_UPDATED, REVIEW_UPDATED, BASE_BRANCH_UPDATED]

condition_variable_types = [
    NUMBER_REVIEWERS,
    REVIEWER,
    NUMBER_ASSIGNEES,
    ASSIGNEE,
    LABEL,
    MERGED,
    MERGEABLE,
    BASE_SYNCED,
    *STATUS_STATE_VARS,
    *REVIEW_STATE_VARS,
]

action_types = [AddPullRequestLabelActionType(), MergePullRequestActionType(), UpdatePullRequestBaseActionType()]
