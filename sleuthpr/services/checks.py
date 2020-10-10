import logging
from typing import Dict
from typing import Optional

from django.utils.text import slugify

from sleuthpr import registry
from sleuthpr.models import ActionResult
from sleuthpr.models import CheckStatus
from sleuthpr.models import ConditionVariableType
from sleuthpr.models import Installation
from sleuthpr.models import PullRequest
from sleuthpr.models import Repository
from sleuthpr.models import Rule
from sleuthpr.models import RuleCheckRun
from sleuthpr.services import rules
from sleuthpr.services.expression import ParsedExpression
from sleuthpr.services.rules import EvaluatedRule
from sleuthpr.services.scm import CheckDetails

logger = logging.getLogger(__name__)


def clear_checks(pull_request: PullRequest):
    RuleCheckRun.objects.filter(pull_request=pull_request).all().delete()
    logger.info(f"Cleared existing checks for PR {pull_request.remote_id}")


def update_checks(installation: Installation, repository: Repository, pull_request: PullRequest):
    ctx = {"pull_request": pull_request}

    existing_checks: Dict = {run.rule.id: run for run in RuleCheckRun.objects.filter(pull_request=pull_request).all()}

    for rule in rules.evaluate_rules(repository, ctx):
        eval_as_status = CheckStatus.SUCCESS if rule.evaluation else CheckStatus.FAILURE
        if not existing_checks.get(rule.id):
            logger.info(f"No existing check for rule {rule.id} found, creating a new one")
            check_id = installation.client.add_check(
                repository.identifier,
                _make_key(rule.rule),
                pull_request.source_sha,
                details=_make_details(ctx, rule),
            )
            RuleCheckRun.objects.create(
                rule=rule.rule,
                status=eval_as_status,
                remote_id=check_id,
                pull_request=pull_request,
            )
        elif existing_checks[rule.id] != eval_as_status:
            logger.info(f"Check outdated for rule {rule.id}, updating")
            installation.client.update_check(
                repository.identifier,
                _make_key(rule.rule),
                pull_request.source_sha,
                details=_make_details(ctx, rule),
                remote_check_id=existing_checks[rule.id].remote_id,
            )
        else:
            logger.info(f"Check exists for rule {rule.id} and is up to date, doing nothing")


def _make_key(rule: Rule):
    return f"{slugify(rule.title)}"


def _make_details(ctx: Dict, rule: EvaluatedRule):
    summary = ""
    var_types: Dict[str, ConditionVariableType] = {}
    for cond in rule.conditions:
        emoji = ":heavy_check_mark:" if cond.evaluation else ":heavy_multiplication_x:"
        summary += f"{emoji} `{cond.condition.expression}`\n"
        for var in ParsedExpression(cond.condition.expression).variables:
            var_types[var.key] = var

    body = "**Triggers**\n"
    triggers = list(rule.rule.triggers.all())
    for trigger in triggers:
        trigger_type = registry.get_trigger_type(trigger.type)
        desc = f" -- {trigger.description}" if trigger.description else ""
        body += f"* {trigger_type.label} (`{trigger.type}`){desc}\n"
    if not triggers:
        body += "\nNone\n"
    body += "\n"
    body += "**Conditions**\n"
    for cond in rule.conditions:
        desc = f" -- {cond.condition.description}" if cond.condition.description else ""
        body += f"* `{cond.condition.expression}`{desc}\n"
    if not rule.conditions:
        body += "\nNone\n"
    body += "\n"
    body += "**Variable values**\n"
    for var in var_types.values():
        value = var(ctx)
        if isinstance(value, list):
            value = ", ".join(value)
        body += f"* {var.label} (`{var.key}`) = `{value}`\n"
    if not var_types:
        body += "\nNone\n"
    body += "\n"
    body += "**Actions when successful**\n"

    head = ctx["pull_request"].source_commit
    for action in rule.rule.ordered_actions:
        action_type = registry.get_action_type(action.type)
        desc = f" -- {action.description}" if action.description else ""
        result: Optional[ActionResult] = action.results.filter(commit=head).first()
        if result:
            result_status = CheckStatus(result.status)
            if result_status == CheckStatus.SUCCESS:
                emoji = ":heavy_check_mark:"
            else:
                emoji = ":heavy_multiplication_x:"
            result_desc = f":: {result.message}"
        else:
            emoji = ":grey_question:"
            result_desc = ""
        body += f"* {emoji} {action_type.label} (`{action.type}`){desc}{result_desc}\n"
    body += "\n(see the pull request history for results)\n"

    body += f"\n[Rule source]({rule.rule.repository.source_url('.sleuth/rules.yml')})"

    return CheckDetails(
        title=rule.rule.description,
        summary=summary,
        body=body,
        success=rule.evaluation,
    )
