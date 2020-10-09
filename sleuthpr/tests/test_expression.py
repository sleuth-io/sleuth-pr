from typing import Callable
from typing import Union
from unittest.mock import patch

import pytest

from sleuthpr.models import ConditionVariableType
from sleuthpr.models import TriState
from sleuthpr.services.expression import ParsedExpression

# pylint: disable=redefined-outer-name


class StubRegistry:
    _vars = {}

    def get_condition_variable_type(self, key):
        return self._vars[key]

    def add_var(self, key: str, expression: Union[Callable, ConditionVariableType]):
        if not isinstance(expression, ConditionVariableType):
            expression = ConditionVariableType(key, f"Variable {key}", type(expression({})), [], expression)

        self._vars[key] = expression


@pytest.fixture
def registry():

    stub = StubRegistry()
    stub.add_var("var", lambda _: 2)
    with patch("sleuthpr.services.expression.registry", new=stub):
        yield stub


def test_expression(registry):

    exp = ParsedExpression("var=2")
    assert {"var"} == {var.key for var in exp.variables}
    assert exp.execute()

    assert not ParsedExpression("var=3").execute()


def test_list(registry):
    registry.add_var("list_var", lambda _: ["foo", "bar"])

    exp = ParsedExpression(f"list_var='foo'")
    assert {"list_var"} == {var.key for var in exp.variables}

    assert exp.execute()

    assert not ParsedExpression("list_var='baz'").execute()
    assert ParsedExpression("list_var!='baz'").execute()


def test_list_size(registry):
    registry.add_var("list_var", lambda _: ["foo", "bar"])

    assert ParsedExpression(f"list_var=2").execute()
    assert ParsedExpression(f"list_var>1").execute()
    assert ParsedExpression(f"list_var>=2").execute()
    assert ParsedExpression(f"list_var<3").execute()
    assert ParsedExpression(f"list_var<=2").execute()
    assert ParsedExpression(f"list_var!=3").execute()


def test_or(registry):
    assert ParsedExpression(f"var=2 or var=5").execute()
    assert not ParsedExpression(f"var=3 or var=5").execute()


def test_and(registry):
    assert not ParsedExpression(f"var=2 and var=5").execute()
    assert ParsedExpression(f"var=2 and var!=5").execute()


def test_identifier_standalone(registry):
    registry.add_var("var", lambda _: True)
    assert ParsedExpression(f"var").execute()
    assert ParsedExpression(f"var and var").execute()
    assert ParsedExpression(f"var or var").execute()


def test_identifier_with_dash(registry):
    registry.add_var("var-bar", lambda _: True)
    assert ParsedExpression(f"var-bar=true").execute()


def test_bool_var(registry):
    registry.add_var("var", lambda _: True)
    assert ParsedExpression(f"var=true").execute()
    assert ParsedExpression(f"var!=false").execute()
    assert ParsedExpression(f"var or var=false").execute()
    assert ParsedExpression(f"var=true or var=false").execute()
    assert ParsedExpression(f"var=true and var=true").execute()
    assert not ParsedExpression(f"var=false").execute()


def test_tristate(registry):
    registry.add_var("var", lambda _: TriState.TRUE)
    assert ParsedExpression(f"var=true").execute()

    registry.add_var("var", lambda _: TriState.FALSE)
    assert ParsedExpression(f"var=false").execute()

    registry.add_var("var", lambda _: TriState.UNKNOWN)
    assert ParsedExpression(f"var=false").execute()


def test_match(registry):
    registry.add_var("match_var", lambda _: "foo")

    exp = ParsedExpression(f"match_var~='f.*'")
    assert {"match_var"} == {var.key for var in exp.variables}
    assert exp.execute()

    assert not ParsedExpression("match_var~='b.*'").execute()
    assert ParsedExpression("match_var~='f.*'").execute()
