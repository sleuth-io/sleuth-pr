from django.utils.text import slugify

from sleuthpr.models import Installation
from sleuthpr.models import PullRequest
from sleuthpr.models import PullRequestCheck
from sleuthpr.models import Repository
from sleuthpr.services import rules


def add_checks(
    installation: Installation, repository: Repository, pull_request: PullRequest
):
    for cond in rules.evaluate_conditions(repository, {"pull_request": pull_request}):
        key = f"{slugify(cond.condition.rule.title)}/{cond.condition.order}"
        remote_id = installation.client.add_check(
            repository.identifier, key, pull_request.source_sha
        )
        PullRequestCheck.objects.create(pull_request=pull_request, remote_id=remote_id)
