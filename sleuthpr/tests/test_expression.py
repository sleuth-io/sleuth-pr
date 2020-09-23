from sleuthpr.services.expression import expr
from sleuthpr.services.expression import ParsedExpression


def test_expression():

    exp = ParsedExpression("number_reviewers=2")
    assert {"number_reviewers"} == {var.key for var in exp.variables}

    assert exp.execute(number_reviewers=2)
    assert not exp.execute(number_reviewers=3)


def test_or():
    exp = expr.parseString("number_reviewers=2 OR number_reviewers=5")[0]
    assert exp.eval(dict(number_reviewers=2))
    assert not exp.eval(dict(number_reviewers=3))


def test_and():
    exp = expr.parseString("number_reviewers=2 AND number_reviewers=3")[0]
    assert not exp.eval(dict(number_reviewers=2))
