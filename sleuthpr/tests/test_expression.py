import pytest

from sleuthpr.services.expression import expr
from sleuthpr.services.expression import ParsedExpression
from sleuthpr.tests.factories import PullRequestFactory
from sleuthpr.tests.factories import PullRequestReviewerFactory


@pytest.mark.django_db
def test_expression():

    pr = _get_pr()

    exp = ParsedExpression("number_reviewers=2")
    assert {"number_reviewers"} == {var.key for var in exp.variables}

    assert exp.execute(pull_request=pr)

    PullRequestReviewerFactory(pull_request=pr)
    assert not exp.execute(pull_request=pr)


def _get_pr():
    pr = PullRequestFactory()
    PullRequestReviewerFactory(pull_request=pr)
    PullRequestReviewerFactory(pull_request=pr)
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
