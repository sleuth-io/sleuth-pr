import logging
from dataclasses import dataclass
from typing import Dict
from typing import List
from typing import Set

import strictyaml

from sleuthpr import registry
from sleuthpr.models import Action
from sleuthpr.models import ActionResult
from sleuthpr.models import CheckStatus
from sleuthpr.models import Condition
from sleuthpr.models import Installation
from sleuthpr.models import PullRequest
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
    doc_data = strictyaml.load(data)

    # clear out existing rules
    repository.rules.all().delete()

    rules: List[Rule] = []
    rules_data = doc_data.get("rules", [])
    for rule_data_orig in rules_data:
        rule_title = next(iter(rule_data_orig.keys()))
        rule_data = rule_data_orig.get(rule_title).value
        rule_description = rule_data.get("description").value if "description" in rule_data else ""

        rule = Rule.objects.create(
            title=rule_title,
            description=rule_description,
            repository=repository,
            order=len(rules),
            line_number=rule_data_orig.start_line,
        )

        conditions = _add_conditions(rule, rule_data)
        if conditions is None:
            rule.delete()
            continue
        else:
            rules.append(rule)

        _add_actions(conditions, rule, rule_data)

        _add_triggers(conditions, rule, rule_data)

    logger.info(f"Loaded {len(rules)} rules")

    return rules


def _add_triggers(conditions, rule, rule_data):
    trigger_types: Set[str] = set()
    if "triggers" in rule_data:
        trigger_types_map = {
            trigger_type_key: registry.get_trigger_type(trigger_type_key).key
            for trigger_type_key in rule_data.get("triggers")
        }
        for trigger_data, trigger_type in (
            item for item in trigger_types_map.items() if item[1] not in trigger_types
        ):
            Trigger.objects.create(rule=rule, type=trigger_type, description="", line_number=trigger_data.start_line)
            trigger_types.add(trigger_type)
    else:
        for condition in conditions:
            try:
                exp = ParsedExpression(condition.expression)
            except Exception as e:
                logger.warning(f"Invalid expression on line {condition.line_number}: {condition.expression}: {e}")
                continue
            for var in exp.variables:
                for trigger_type in (trig for trig in var.default_triggers if trig.key not in trigger_types):
                    Trigger.objects.create(
                        rule=rule,
                        type=trigger_type.key,
                        description=f"Implied from variable '{var.key}'",
                        line_number=condition.line_number,
                    )
                    trigger_types.add(trigger_type.key)


def _add_actions(conditions, rule, rule_data):
    actions: List[Action] = []
    actions_data = rule_data.get("actions", [])
    used_conditions: Set[str] = {cond.expression for cond in conditions}
    for action_data in actions_data:
        if isinstance(action_data.value, str):
            action_type = registry.get_action_type(action_data.value)
            params_data = {}
        else:
            action_type = registry.get_action_type(next(iter(action_data.keys())).value)
            params_data = action_data.get(action_type.key).data
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

        for condition_str in (cond for cond in action_type.conditions if cond not in used_conditions):
            conditions.append(
                Condition.objects.create(
                    rule=rule,
                    description=f"Implied from action '{action_type.key}'",
                    expression=condition_str,
                    order=len(conditions),
                    line_number=action_data.start_line,
                )
            )
            used_conditions.add(condition_str)

        action = Action.objects.create(
            rule=rule,
            description=description,
            parameters=parameters,
            type=action_type.key,
            order=len(actions),
            line_number=action_data.start_line,
        )
        actions.append(action)


def _add_conditions(rule, rule_data):
    conditions: List[Condition] = []
    conditions_data = rule_data.get("conditions", [])
    for condition_data_orig in conditions_data:
        condition_data = condition_data_orig.data
        if isinstance(condition_data, str):
            expression = condition_data
            description = ""
        else:
            description = condition_data.get("description", "")
            expression = condition_data.get("expression")

        try:
            ParsedExpression(expression)
        except Exception:
            logger.warning(f"Invalid expression on line {condition_data_orig.start_line}: {expression}")
            return None

        condition = Condition.objects.create(
            rule=rule,
            description=description,
            expression=expression,
            order=len(conditions),
            line_number=condition_data_orig.start_line,
        )
        conditions.append(condition)
    return conditions


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
        logger.info(f"[eval] Evaluating rule {rule.id}")
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
    logger.info(f"[exec] Evaluating rule {rule.id} - {rule.title}")
    repository = rule.repository
    installation = repository.installation
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
        pr: PullRequest = context["pull_request"]
        head = pr.source_commit
        for action in rule.actions.order_by("order").all():
            logger.info(f"Executing action {action.type}")
            action_type = registry.get_action_type(action.type)
            result, message = action_type.execute(action, context)
            _update_action_result(installation, repository, pr, action, head, message, result)

            if result != CheckStatus.SUCCESS:
                logger.info(f"Action {action.type} failed with status {result}, aborting")
                break


def _update_action_result(
    installation: Installation, repository: Repository, pull_request: PullRequest, action, head, message, result
):
    existing_result = ActionResult.objects.filter(action=action, commit=head).first()
    if not existing_result:
        existing_result = ActionResult(action=action, commit=head)
    existing_result.status = result
    existing_result.message = message
    existing_result.save()
    from sleuthpr.services import checks

    checks.update_checks(installation, repository, pull_request)
