import pytest

from sleuthpr.services.rules import refresh_from_data
from sleuthpr.tests.factories import RepositoryFactory


@pytest.mark.django_db
def test_basic():

    data = """
rules:
  - ensure-lots-of-reviewers:
      description: "Ensure lots-of-reviewers is on big pull requests"
      triggers:
        - pr_updated
      conditions:
        - description: "Number of reviewers is more than 3"
          expression: "number_reviewers>3"
      actions:
        - add_pull_request_label: "lots-of-reviewers"
        - add_pull_request_label:
            description: "blah"
            parameters: "lots-of-reviewers2"
"""
    repository = RepositoryFactory()
    rules = refresh_from_data(repository, data)
    assert 1 == len(rules)

    rule = rules[0]
    assert "ensure-lots-of-reviewers" == rule.title
    assert "Ensure lots-of-reviewers is on big pull requests" == rule.description
    assert 1 == len(rule.conditions.all())
    assert 2 == rule.line_number

    assert 1 == len(rule.triggers.all())
    trigger = rule.triggers.filter(type="pr_updated").first()
    assert "pr_updated" == trigger.type
    assert 5 == trigger.line_number

    condition = rule.conditions.all()[0]
    assert "Number of reviewers is more than 3" == condition.description
    assert "number_reviewers>3" == condition.expression
    assert 2 == len(rule.actions.all())
    assert 7 == condition.line_number

    action = rule.actions.all()[0]
    assert "add_pull_request_label" == action.type
    assert "lots-of-reviewers" == action.parameters.get("value")
    assert 10 == action.line_number

    action = rule.actions.all()[1]
    assert "add_pull_request_label" == action.type
    assert "blah" == action.description
    assert "lots-of-reviewers2" == action.parameters.get("value")


@pytest.mark.django_db
def test_guess_triggers():

    data = """
rules:
  - ensure-lots-of-reviewers:
      description: "Ensure lots-of-reviewers is on big pull requests"
      conditions:
        - description: "Number of reviewers is more than 3"
          expression: "number_reviewers>3"
      actions:
        - add_pull_request_label: "lots-of-reviewers"
"""
    repository = RepositoryFactory()
    rule = refresh_from_data(repository, data)[0]

    assert 2 == len(rule.triggers.all())
    assert {"pr_created", "pr_updated"} == set(t.type for t in rule.triggers.all())


@pytest.mark.django_db
def test_no_action_params():

    data = """
rules:
  - ensure-lots-of-reviewers:
      description: "Ensure lots-of-reviewers is on big pull requests"
      triggers:
        - base_branch_updated
      actions:
        - update_pull_request_base
"""
    repository = RepositoryFactory()
    rule = refresh_from_data(repository, data)[0]

    assert 1 == len(rule.triggers.all())
    assert {"update_pull_request_base"} == set(t.type for t in rule.actions.all())


@pytest.mark.django_db
def test_simple():

    data = """
rules:
  - keep_uptodate:
      triggers:
        - base_branch_updated
      actions:
        - update_pull_request_base
"""
    repository = RepositoryFactory()
    rule = refresh_from_data(repository, data)[0]

    assert 1 == len(rule.triggers.all())
    assert 1 == len(rule.conditions.all())
    assert {"update_pull_request_base"} == set(t.type for t in rule.actions.all())


@pytest.mark.django_db
def test_ignore_invalid():

    data = """
rules:
  - ensure-lots-of-reviewers:
      conditions:
        - not-exist=0
      actions:
        - update_pull_request_base
"""
    repository = RepositoryFactory()
    assert 0 == len(refresh_from_data(repository, data))


@pytest.mark.django_db
def test_dup_implied_triggers():

    data = """
rules:
  - ensure-lots-of-reviewers:
      actions:
        - merge_pull_request
        - merge_pull_request
        - merge_pull_request
"""
    repository = RepositoryFactory()
    rule = refresh_from_data(repository, data)[0]

    assert 4 == len(rule.triggers.all())
    assert 3 == len(rule.conditions.all())
