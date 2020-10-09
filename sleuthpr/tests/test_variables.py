import pytest

from sleuthpr.models import CheckStatus
from sleuthpr.models import PullRequest
from sleuthpr.models import ReviewState
from sleuthpr.models import TriState
from sleuthpr.services.expression import ParsedExpression
from sleuthpr.tests.factories import PullRequestAssigneeFactory
from sleuthpr.tests.factories import PullRequestFactory
from sleuthpr.tests.factories import PullRequestLabelFactory
from sleuthpr.tests.factories import PullRequestReviewerFactory
from sleuthpr.tests.factories import PullRequestStatusFactory
from sleuthpr.tests.factories import RepositoryBranchFactory
from sleuthpr.tests.factories import RepositoryCommitFactory
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
    assert ParsedExpression(f"behind=false").execute(pull_request=pr)
    assert ParsedExpression(f"closed=false").execute(pull_request=pr)
    assert ParsedExpression(f"closed=false").execute(pull_request=pr)
    assert ParsedExpression(f"author='{pr.author.username}'")
    assert ParsedExpression(f"pull_request_author='{pr.author.username}'")
    assert ParsedExpression(f"commit_author='{pr.commits.first().author.username}'")
    assert ParsedExpression(f"title='{pr.title}'")
    assert ParsedExpression(f"description='{pr.description}'")
    assert ParsedExpression(f"commit_message='{pr.commits.first().message}'")
    assert ParsedExpression(f"commit_message!='blah'")
    assert ParsedExpression(f"draft=false")
    assert ParsedExpression(f"conflict=false")


@pytest.mark.django_db
def test_statuses():
    pr = PullRequestFactory(merged=False, mergeable=True)
    for status in CheckStatus:
        PullRequestStatusFactory(pull_request=pr, context=f"ctx/{status}", state=status)

    for status in CheckStatus:
        assert ParsedExpression(f"status-{status}='ctx/{status}'").execute(pull_request=pr)


@pytest.mark.django_db
def test_behind():
    repo = RepositoryFactory()
    pr: PullRequest = PullRequestFactory(repository=repo, merged=False, mergeable=True)

    assert ParsedExpression(f"behind=false").execute(pull_request=pr)

    RepositoryBranchFactory.add_commit(
        repo, pr.base_branch_name, RepositoryCommitFactory(repository=repo, sha="base-head")
    )

    assert ParsedExpression(f"behind").execute(pull_request=pr)


@pytest.mark.django_db
def test_review_state():
    pr = PullRequestFactory(merged=False, mergeable=True)
    reviewers = {}
    for state in ReviewState:
        reviewers[state] = PullRequestReviewerFactory(pull_request=pr, state=state).user.username

    for state in ReviewState:
        assert ParsedExpression(f"review-{state}='{reviewers[state]}'").execute(pull_request=pr)


def _get_pr() -> PullRequest:
    pr = PullRequestFactory(merged=False, mergeable=TriState.TRUE)
    PullRequestReviewerFactory(pull_request=pr)
    PullRequestReviewerFactory(pull_request=pr)
    PullRequestAssigneeFactory(pull_request=pr)
    PullRequestLabelFactory(pull_request=pr, value="label1")
    PullRequestLabelFactory(pull_request=pr, value="label2")
    return pr
