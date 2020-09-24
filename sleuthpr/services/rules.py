import logging
from typing import Dict
from typing import List
from typing import Set

import yaml

from sleuthpr import registry
from sleuthpr.models import Action
from sleuthpr.models import ActionType
from sleuthpr.models import Condition
from sleuthpr.models import Repository
from sleuthpr.models import Rule
from sleuthpr.models import Trigger
from sleuthpr.models import TriggerType
from sleuthpr.services.expression import ParsedExpression

logger = logging.getLogger(__name__)


def refresh(repository: Repository, data: str) -> List[Rule]:
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
            description = condition_data.get("description", "")
            expression = condition_data.get("expression")
            condition = Condition.objects.create(
                rule=rule,
                description=description,
                expression=expression,
                order=len(conditions),
            )
            conditions.append(condition)

        trigger_types: Set[str] = set()
        triggers_data = rule_data.get("triggers", [])
        if not triggers_data:
            for condition in conditions:
                exp = ParsedExpression(condition.expression)
                for var in exp.variables:
                    for trigger_type_key in var.default_triggers:
                        trigger_type = registry.get_trigger_type(trigger_type_key)
                        trigger_types.add(trigger_type.key)
        else:
            trigger_types = set(
                registry.get_trigger_type(trigger_type_key).key
                for trigger_type_key in triggers_data
            )

        for trigger_type in trigger_types:
            Trigger.objects.create(rule=rule, type=trigger_type)

        actions: List[Action] = []
        actions_data = rule_data.get("actions", [])
        for action_data in actions_data:
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

            action = Action.objects.create(
                rule=rule,
                description=description,
                parameters=parameters,
                type=action_type.key,
                order=len(actions),
            )
            actions.append(action)

        logger.info(f"Loaded {len(rules)} rules")

    return rules


def evaluate(repository: Repository, trigger_type: TriggerType, pr_data: Dict):
    rules = (
        repository.rules.filter(triggers__type__contains=trigger_type.key)
        .order_by("order")
        .all()
    )
    for rule in rules:
        logger.info(f"Evaluating rule {rule.id}")
        for condition in rule.conditions.order_by("order").all():
            expression = ParsedExpression(condition.expression)
            logger.info(f"Evaluating condition {condition.expression}")
            if expression.execute(number_reviewers=len(pr_data["requested_reviewers"])):
                logger.info("Condition was true")
                for action in rule.actions.order_by("order").all():
                    logger.info(f"Executing action {action.type}")
                    action_type = registry.get_action_type(action.type)
                    action_type.execute(action, pr_data)
            else:
                logger.info("Condition was false")
