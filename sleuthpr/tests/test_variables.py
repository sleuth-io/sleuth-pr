import pytest

from sleuthpr.models import CheckStatus
from sleuthpr.models import PullRequest
from sleuthpr.models import ReviewState
from sleuthpr.services.expression import ParsedExpression
from sleuthpr.tests.factories import PullRequestAssigneeFactory
from sleuthpr.tests.factories import PullRequestFactory
from sleuthpr.tests.factories import PullRequestLabelFactory
from sleuthpr.tests.factories import PullRequestReviewerFactory
from sleuthpr.tests.factories import PullRequestStatusFactory
from sleuthpr.tests.factories import RepositoryBranchFactory
from sleuthpr.tests.factories import RepositoryCommitFactory
from sleuthpr.tests.factories import RepositoryCommitParentFactory
from sleuthpr.tests.factories import RepositoryFactory


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


@pytest.mark.django_db
def test_statuses():
    pr = PullRequestFactory(merged=False, mergeable=True)
    for status in CheckStatus:
        PullRequestStatusFactory(pull_request=pr, context=f"ctx/{status}", state=status)

    for status in CheckStatus:
        assert ParsedExpression(f"status-{status}='ctx/{status}'").execute(pull_request=pr)


@pytest.mark.django_db
def test_base_synced():
    repo = RepositoryFactory()
    pr = PullRequestFactory(repository=repo, merged=False, mergeable=True)
    RepositoryBranchFactory(repository=repo, head_sha="master-head")
    master_head = RepositoryCommitFactory(repository=repo, sha="master-head")
    pr_head = RepositoryCommitFactory(repository=repo, sha="pr-head", pull_request=pr)
    RepositoryCommitParentFactory(repository=repo, child=pr_head, parent=master_head)

    assert ParsedExpression(f"base_synced").execute(pull_request=pr)


@pytest.mark.django_db
def test_review_state():
    pr = PullRequestFactory(merged=False, mergeable=True)
    reviewers = {}
    for state in ReviewState:
        reviewers[state] = PullRequestReviewerFactory(pull_request=pr, state=state).user.username

    for state in ReviewState:
        assert ParsedExpression(f"review-{state}='{reviewers[state]}'").execute(pull_request=pr)


def _get_pr() -> PullRequest:
    pr = PullRequestFactory(merged=False, mergeable=True)
    PullRequestReviewerFactory(pull_request=pr)
    PullRequestReviewerFactory(pull_request=pr)
    PullRequestAssigneeFactory(pull_request=pr)
    PullRequestLabelFactory(pull_request=pr, value="label1")
    PullRequestLabelFactory(pull_request=pr, value="label2")
    return pr
