from typing import List
from typing import Set

import yaml

from sleuthpr.models import Action
from sleuthpr.models import ActionType
from sleuthpr.models import Condition
from sleuthpr.models import ConditionVariable
from sleuthpr.models import Repository
from sleuthpr.models import Rule
from sleuthpr.models import Trigger
from sleuthpr.models import TriggerType
from sleuthpr.services.expression import ParsedExpression


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
                    for trigger_type in var.default_triggers:
                        trigger_types.add(trigger_type.value)
        else:
            trigger_types = set(triggers_data)

        for trigger_name in trigger_types:
            Trigger.objects.create(rule=rule, type=TriggerType(trigger_name))

        actions: List[Action] = []
        actions_data = rule_data.get("actions", [])
        for action_data in actions_data:
            action_type = ActionType(next(iter(action_data.keys())))
            params_data = action_data.get(action_type.value)
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
                type=action_type,
                order=len(actions),
            )
            actions.append(action)

    return rules
