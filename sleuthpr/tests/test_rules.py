import pytest

from sleuthpr.models import ActionType
from sleuthpr.services.rules import refresh
from sleuthpr.tests.factories import RepositoryFactory


@pytest.mark.django_db
def test_basic():

    data = """
rules:
  - ensure-lots-of-reviewers:
      description: "Ensure lots-of-reviewers is on big pull requests"
      conditions:
        - description: "Number of reviewers is more than 3"
          expression: "number_reviewers>3"
      actions:
        - add_label: "lots-of-reviewers"
        - add_label: 
            description: "blah"
            parameters: "lots-of-reviewers2"
"""
    repository = RepositoryFactory()
    rules = refresh(repository, data)
    assert 1 == len(rules)

    rule = rules[0]
    assert "ensure-lots-of-reviewers" == rule.title
    assert "Ensure lots-of-reviewers is on big pull requests" == rule.description
    assert 1 == len(rule.conditions.all())

    condition = rule.conditions.all()[0]
    assert "Number of reviewers is more than 3" == condition.description
    assert "number_reviewers>3" == condition.expression
    assert 2 == len(rule.actions.all())

    action = rule.actions.all()[0]
    assert ActionType.ADD_LABEL == action.type
    assert "lots-of-reviewers" == action.parameters.get("value")

    action = rule.actions.all()[1]
    assert ActionType.ADD_LABEL == action.type
    assert "blah" == action.description
    assert "lots-of-reviewers2" == action.parameters.get("value")


