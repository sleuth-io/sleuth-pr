from typing import List

import yaml

from sleuthpr.models import Rule, Condition, Repository, Action, ActionType


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

        rule = Rule.objects.create(title=rule_title, description=rule_description, repository=repository,
                                   order=len(rules))
        rules.append(rule)

        conditions: List[Condition] = []
        conditions_data = rule_data.get("conditions", [])
        for condition_data in conditions_data:
            description = condition_data.get("description", "")
            expression = condition_data.get("expression")
            condition = Condition.objects.create(rule=rule, description=description, expression=expression,
                                                 order=len(conditions))
            conditions.append(condition)

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

            action = Action.objects.create(rule=rule, description=description, parameters=parameters,
                                           type=action_type, order=len(actions))
            actions.append(action)

    return rules
