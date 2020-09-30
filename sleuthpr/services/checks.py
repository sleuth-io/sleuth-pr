import logging
from typing import Dict

from django.utils.text import slugify

from sleuthpr.models import CheckStatus
from sleuthpr.models import Condition
from sleuthpr.models import ConditionCheckRun
from sleuthpr.models import Installation
from sleuthpr.models import PullRequest
from sleuthpr.models import Repository
from sleuthpr.services import rules
from sleuthpr.services.expression import ParsedExpression
from sleuthpr.services.scm import CheckDetails


logger = logging.getLogger(__name__)


def clear_checks(pull_request: PullRequest):
    ConditionCheckRun.objects.filter(pull_request=pull_request).all().delete()
    logger.info(f"Cleared existing checks for PR {pull_request.remote_id}")


def update_checks(installation: Installation, repository: Repository, pull_request: PullRequest):
    ctx = {"pull_request": pull_request}

    existing_checks: Dict = {
        run.condition.id: run for run in ConditionCheckRun.objects.filter(pull_request=pull_request).all()
    }

    for cond in rules.evaluate_conditions(repository, ctx):
        eval_as_status = CheckStatus.SUCCESS if cond.evaluation else CheckStatus.FAILURE
        if not existing_checks.get(cond.condition.id):
            logger.info(f"No existing check for condition {cond.condition.id} found, creating a new one")
            check_id = installation.client.add_check(
                repository.identifier,
                _make_key(cond.condition),
                pull_request.source_sha,
                details=_make_details(ctx, cond.condition, cond.evaluation),
            )
            ConditionCheckRun.objects.create(
                condition=cond.condition,
                status=eval_as_status,
                remote_id=check_id,
                pull_request=pull_request,
            )
        elif existing_checks[cond.condition.id] != eval_as_status:
            logger.info(f"Check outdated for condition {cond.condition.id}, updating")
            installation.client.update_check(
                repository.identifier,
                _make_key(cond.condition),
                pull_request.source_sha,
                details=_make_details(ctx, cond.condition, cond.evaluation),
                remote_check_id=existing_checks[cond.condition.id].remote_id,
            )
        else:
            logger.info(f"Check exists for condition {cond.condition.id} and is up to date, doing nothing")


def _make_key(condition: Condition):
    return f"{slugify(condition.rule.title)}/{condition.order}"


def _make_details(ctx: Dict, condition: Condition, result: bool):
    body = "Variable values:\n"
    for var in ParsedExpression(condition.expression).variables:
        body += f"* {var.label} ({var.key}) = {var(ctx)}"
    return CheckDetails(
        title=f"Rule {condition.rule.title}, Condition {condition.order}",
        summary=f"Expression: {condition.expression}",
        body=body,
        success=result,
    )
