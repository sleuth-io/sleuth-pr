from sleuthpr.models import TriggerType

PR_UPDATED = TriggerType("pr_updated", "Pull request updated")
PR_CREATED = TriggerType("pr_created", "Pull request created")
PR_CLOSED = TriggerType("pr_closed", "Pull request closed")
PR_REOPENED = TriggerType("pr_reopened", "Pull request reopened")
STATUS_UPDATED = TriggerType("status_updated", "Commit status updated")
REVIEW_UPDATED = TriggerType("review_updated", "Pull request review updated")
BASE_BRANCH_UPDATED = TriggerType("base_branch_updated", "Pull request's base branch updated")
