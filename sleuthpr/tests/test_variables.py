import pytest

from sleuthpr.models import PullRequest
from sleuthpr.services.expression import ParsedExpression
from sleuthpr.tests.factories import PullRequestAssigneeFactory
from sleuthpr.tests.factories import PullRequestFactory
from sleuthpr.tests.factories import PullRequestLabelFactory
from sleuthpr.tests.factories import PullRequestReviewerFactory


@pytest.mark.django_db
def test_variables():

    pr = _get_pr()

    assert ParsedExpression("number_reviewers=2").execute(pull_request=pr)
    assert ParsedExpression(f"reviewer='{pr.reviewers.first().user.username}'").execute(pull_request=pr)
    assert ParsedExpression(f"reviewer!='blah'").execute(pull_request=pr)
    assert ParsedExpression("number_assignees=1").execute(pull_request=pr)
    assert ParsedExpression(f"assignee='{pr.assignees.first().user.username}'").execute(pull_request=pr)
    assert ParsedExpression(f"assignee!='blah'").execute(pull_request=pr)

    assert ParsedExpression(f"label='label1'").execute(pull_request=pr)
    assert ParsedExpression(f"label!='blah'").execute(pull_request=pr)

    assert ParsedExpression(f"merged=false").execute(pull_request=pr)
    assert ParsedExpression(f"mergeable").execute(pull_request=pr)
    assert ParsedExpression(f"mergeable=true").execute(pull_request=pr)
    assert ParsedExpression(f"merged=false and mergeable").execute(pull_request=pr)
    assert ParsedExpression(f"merged or mergeable").execute(pull_request=pr)


def _get_pr() -> PullRequest:
    pr = PullRequestFactory(merged=False, mergeable=True)
    PullRequestReviewerFactory(pull_request=pr)
    PullRequestReviewerFactory(pull_request=pr)
    PullRequestAssigneeFactory(pull_request=pr)
    PullRequestLabelFactory(pull_request=pr, value="label1")
    PullRequestLabelFactory(pull_request=pr, value="label2")
    return pr
