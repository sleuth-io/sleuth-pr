import logging
from dataclasses import dataclass
from typing import Dict
from typing import List
from typing import Set

import yaml

from sleuthpr import registry
from sleuthpr.models import Action
from sleuthpr.models import Condition
from sleuthpr.models import Installation
from sleuthpr.models import Repository
from sleuthpr.models import Rule
from sleuthpr.models import Trigger
from sleuthpr.models import TriggerType
from sleuthpr.services.expression import ParsedExpression

logger = logging.getLogger(__name__)


def refresh(installation: Installation, repository: Repository):
    contents = installation.client.get_content(repository.identifier, ".sleuth/rules.yml")
    if contents:
        refresh_from_data(repository, contents)


def refresh_from_data(repository: Repository, data: str) -> List[Rule]:
    doc_data = yaml.safe_load(data)

    # clear out existing rules
    repository.rules.all().delete()

    rules: List[Rule] = []
    rules_data = doc_data.get("rules", [])
    for rule_data in rules_data:
        rule_title = next(iter(rule_data.keys()))
        rule_data = rule_data.get(rule_title)
        rule_description = rule_data.get("description", "")

        rule = Rule.objects.create(
            title=rule_title,
            description=rule_description,
            repository=repository,
            order=len(rules),
        )
        rules.append(rule)

        conditions: List[Condition] = []
        conditions_data = rule_data.get("conditions", [])
        for condition_data in conditions_data:
            if isinstance(condition_data, str):
                expression = condition_data
                description = ""
            else:
                description = condition_data.get("description", "")
                expression = condition_data.get("expression")
            condition = Condition.objects.create(
                rule=rule,
                description=description,
                expression=expression,
                order=len(conditions),
            )
            conditions.append(condition)

        actions: List[Action] = []
        actions_data = rule_data.get("actions", [])
        for action_data in actions_data:
            if isinstance(action_data, str):
                action_type = registry.get_action_type(action_data)
                params_data = {}
            else:
                action_type = registry.get_action_type(next(iter(action_data.keys())))
                params_data = action_data.get(action_type.key)
            parameters = {}
            if isinstance(params_data, str):
                parameters["value"] = params_data
                description = ""
            elif isinstance(params_data, dict):
                parameters_data = params_data.get("parameters", {})
                if isinstance(parameters_data, str):
                    parameters["value"] = parameters_data
                else:
                    parameters.update(parameters_data)
                description = params_data.get("description", "")
            else:
                raise ValueError("Invalid parameters")

            for condition_str in action_type.conditions:
                conditions.append(
                    Condition.objects.create(
                        rule=rule,
                        description=f"Implied from action {action_type.key}",
                        expression=condition_str,
                        order=len(conditions),
                    )
                )

            action = Action.objects.create(
                rule=rule,
                description=description,
                parameters=parameters,
                type=action_type.key,
                order=len(actions),
            )
            actions.append(action)

        triggers: Set[Trigger] = set()
        triggers_data = rule_data.get("triggers", [])
        if not triggers_data:
            for condition in conditions:
                exp = ParsedExpression(condition.expression)
                for var in exp.variables:
                    for trigger_type in var.default_triggers:
                        triggers.add(
                            Trigger.objects.create(
                                rule=rule, type=trigger_type.key, description=f"Implied from variable {var.key}"
                            )
                        )
        else:
            trigger_types = set(registry.get_trigger_type(trigger_type_key).key for trigger_type_key in triggers_data)
            for trigger_type in trigger_types:
                Trigger.objects.create(rule=rule, type=trigger_type, description="")

        logger.info(f"Loaded {len(rules)} rules")

    return rules


@dataclass
class EvaluatedCondition:
    condition: Condition
    evaluation: bool


class EvaluatedRule:
    def __init__(self, rule: Rule, conditions: List[EvaluatedCondition]):
        self.conditions = conditions
        self.rule = rule
        self.id = rule.id
        self.evaluation = all(c.evaluation for c in conditions)


def evaluate_rules(repository: Repository, context: Dict) -> List[EvaluatedRule]:
    result = []
    for rule in repository.ordered_rules:
        logger.info(f"Evaluating rule {rule.id}")
        conditions: List[EvaluatedCondition] = []
        for condition in rule.ordered_conditions:
            expression = ParsedExpression(condition.expression)
            conditions.append(EvaluatedCondition(condition=condition, evaluation=expression.execute(**context)))
        result.append(EvaluatedRule(rule, conditions))
    return result


def evaluate(repository: Repository, trigger_type: TriggerType, context: Dict):
    rules = repository.rules.filter(triggers__type__contains=trigger_type.key).order_by("order").all()
    for rule in rules:
        _evaluate_rule(rule, context)


def _evaluate_rule(rule: Rule, context: Dict):
    logger.info(f"Evaluating rule {rule.id} - {rule.title}")
    conditions_ok = True
    for condition in rule.ordered_conditions:
        expression = ParsedExpression(condition.expression)
        logger.info(f"Evaluating condition {condition.expression}")
        if expression.execute(**context):
            logger.info("Condition was true")
        else:
            logger.info("Condition was false")
            conditions_ok = False

    if conditions_ok:
        logger.info("All conditions ok, executing actions")
        for action in rule.actions.order_by("order").all():
            logger.info(f"Executing action {action.type}")
            action_type = registry.get_action_type(action.type)
            if not action_type.execute(action, context):
                logger.info(f"Action {action.type} failed, aborting")
                break
