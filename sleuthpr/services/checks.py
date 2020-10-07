import logging
from typing import Dict

from django.utils.text import slugify

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
        summary = f"{cond.condition.expression} evaluates to {str(cond.evaluation).lower()}\n"
        for var in ParsedExpression(cond.condition.expression).variables:
            var_types[var.key] = var

    body = "Triggers:\n"
    for trigger in rule.rule.triggers.all():
        body += f"* {trigger.type}\n"
    body += "\n"
    body += "Conditions:\n"
    for cond in rule.conditions:
        body += f"* {cond.condition.expression}\n"
    body += "\n"
    body += "Variable values:\n"
    for var in var_types.values():
        body += f"* {var.label} ({var.key}) = {var(ctx)}\n"
    body += "\n"
    body += "Actions when successful:\n"
    for action in rule.rule.ordered_actions:
        body += f"* {action.type}\n"

    body += f"\n[source]({rule.rule.repository.source_url('.sleuth/rules.yml')})"

    return CheckDetails(
        title=rule.rule.description,
        summary=summary,
        body=body,
        success=rule.evaluation,
    )
