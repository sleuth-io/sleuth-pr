from sleuthpr.actions import AddLabelActionType
from sleuthpr.triggers import PR_CREATED
from sleuthpr.triggers import PR_UPDATED
from sleuthpr.variables import NumberReviewersVariableType

trigger_types = [PR_UPDATED, PR_CREATED]


condition_variable_types = [NumberReviewersVariableType()]

action_types = [AddLabelActionType()]
