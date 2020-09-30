import pytest

from sleuthpr.models import PullRequest
from sleuthpr.services.expression import expr
from sleuthpr.services.expression import ParsedExpression
from sleuthpr.tests.factories import PullRequestAssigneeFactory
from sleuthpr.tests.factories import PullRequestFactory
from sleuthpr.tests.factories import PullRequestLabelFactory
from sleuthpr.tests.factories import PullRequestReviewerFactory


@pytest.mark.django_db
def test_expression():

    pr = _get_pr()

    exp = ParsedExpression("number_reviewers=2")
    assert {"number_reviewers"} == {var.key for var in exp.variables}

    assert exp.execute(pull_request=pr)

    PullRequestReviewerFactory(pull_request=pr)
    assert not exp.execute(pull_request=pr)


@pytest.mark.django_db
def test_list():

    pr = _get_pr()

    username_in_list = pr.reviewers.first().user.username

    exp = ParsedExpression(f"reviewer='{username_in_list}'")
    assert {"reviewer"} == {var.key for var in exp.variables}

    assert exp.execute(pull_request=pr)

    pr.reviewers.filter(user__username=username_in_list).delete()
    assert not exp.execute(pull_request=pr)


@pytest.mark.django_db
def test_not_list():

    pr = _get_pr()

    username_in_list = pr.reviewers.first().user.username

    exp = ParsedExpression(f"reviewer!='{username_in_list}'")
    assert {"reviewer"} == {var.key for var in exp.variables}

    assert not exp.execute(pull_request=pr)

    pr.reviewers.filter(user__username=username_in_list).delete()
    assert exp.execute(pull_request=pr)


def _get_pr() -> PullRequest:
    pr = PullRequestFactory()
    PullRequestReviewerFactory(pull_request=pr)
    PullRequestReviewerFactory(pull_request=pr)
    PullRequestAssigneeFactory(pull_request=pr)
    PullRequestLabelFactory(pull_request=pr, value="label1")
    PullRequestLabelFactory(pull_request=pr, value="label2")
    return pr


@pytest.mark.django_db
def test_or():
    pr = _get_pr()
    exp = expr.parseString("number_reviewers=2 OR number_reviewers=5")[0]
    assert exp.eval(dict(pull_request=pr))
    PullRequestReviewerFactory(pull_request=pr)
    assert not exp.eval(dict(pull_request=pr))


@pytest.mark.django_db
def test_and():
    pr = _get_pr()
    exp = expr.parseString("number_reviewers=2 AND number_reviewers=3")[0]
    assert not exp.eval(dict(pull_request=pr))
