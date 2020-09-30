from sleuthpr.actions import AddLabelActionType
from sleuthpr.triggers import PR_CREATED
from sleuthpr.triggers import PR_UPDATED
from sleuthpr.variables import ASSIGNEE
from sleuthpr.variables import LABEL
from sleuthpr.variables import MERGEABLE
from sleuthpr.variables import MERGED
from sleuthpr.variables import NUMBER_ASSIGNEES
from sleuthpr.variables import NUMBER_REVIEWERS
from sleuthpr.variables import REVIEWER

trigger_types = [PR_UPDATED, PR_CREATED]

condition_variable_types = [
    NUMBER_REVIEWERS,
    REVIEWER,
    NUMBER_ASSIGNEES,
    ASSIGNEE,
    LABEL,
    MERGED,
    MERGEABLE,
]

action_types = [AddLabelActionType()]
