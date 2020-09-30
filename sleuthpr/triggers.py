from sleuthpr.models import TriggerType

PR_UPDATED = TriggerType("pr_updated", "Pull request updated")
PR_CREATED = TriggerType("pr_created", "Pull request created")
PR_CLOSED = TriggerType("pr_closed", "Pull request closed")
