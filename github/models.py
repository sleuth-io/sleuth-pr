from dataclasses import dataclass
from enum import Enum
from typing import List, Dict

from django.db import models
from django.db.models import CASCADE, TextChoices
from django.utils.timezone import now
from django.utils.translation import gettext_lazy as _


class Installation(models.Model):
    remote_id = models.CharField(max_length=512, db_index=True)
    target_type = models.CharField(max_length=50)
    target_id = models.CharField(max_length=255)
    on = models.DateTimeField(default=now, verbose_name=_("created on"), db_index=True)
    provider = models.CharField(max_length=50)


class Repository(models.Model):
    installation = models.ForeignKey(
        Installation, on_delete=CASCADE, related_name="repositories", verbose_name=_("installation"),
    )
    name = models.CharField(max_length=255)
    owner = models.CharField(max_length=255)


class ExternalUser(models.Model):
    name = models.CharField(max_length=512, verbose_name=_("name"), db_index=True)
    email = models.EmailField(max_length=512, verbose_name=_("email"), blank=True, db_index=True)
    username = models.CharField(max_length=512, blank=True, verbose_name=_("username"), db_index=True)
    remote_id = models.CharField(max_length=512, blank=True, null=True, verbose_name=_("uid"), db_index=True)

    installation = models.CharField(max_length=255, verbose_name=_("provider"), db_index=True)


class PullRequest(models.Model):
    title = models.TextField(default="", max_length=16384, verbose_name=_("title"), db_index=True)
    description = models.TextField(max_length=16384, blank=True, verbose_name=_("description"))
    on = models.DateTimeField(default=now, verbose_name=_("created on"), db_index=True)
    remote_id = models.CharField(max_length=512, db_index=True)
    source_branch_name = models.CharField(
        max_length=1024, blank=True, null=True, verbose_name=_("source branch name"), db_index=True,
    )
    url = models.URLField(max_length=1024, blank=True, verbose_name=_("url"))
    repository = models.ForeignKey(
        Repository, on_delete=CASCADE, related_name="pull_requests", verbose_name=_("repository"),
    )


class Rule(models.Model):
    description = models.TextField(max_length=16384, blank=True, verbose_name=_("description"))
    on = models.DateTimeField(default=now, verbose_name=_("created on"), db_index=True)
    repository = models.ForeignKey(
        Repository, on_delete=CASCADE, related_name="rules", verbose_name=_("repository"),
    )


class TriggerType(TextChoices):
    PR_UPDATED = ("pr_updated", "PR Updated")
    PR_CREATED = ("pr_created", "PR Created")
    CRON = ("cron", "Every 5 minutes")


@dataclass
class ActionType:
    key: str
    description: str

    def execute(self, context: Dict):
        pass


@dataclass
class ConditionVariable:
    key: str
    title: str
    description: str

    default_triggers: List[TriggerType]


class Context:
    pull_request: PullRequest
    repository: Repository
    installation: Installation


class Trigger(models.Model):
    rule = models.ForeignKey(
        Rule, on_delete=CASCADE, related_name="pull_requests", verbose_name=_("installation"),
    )
    type = models.CharField(max_length=30, choices=TriggerType.choices)


class Condition(models.Model):
    description = models.TextField(max_length=16384, blank=True, verbose_name=_("description"))
    expression = models.TextField(max_length=16384, blank=True, verbose_name=_("expression"))
    on = models.DateTimeField(default=now, verbose_name=_("created on"), db_index=True)
    rule = models.ForeignKey(
        Rule, on_delete=CASCADE, related_name="pull_requests", verbose_name=_("installation"),
    )


class Action(models.Model):
    type = models.CharField(max_length=255, verbose_name=_("type"), db_index=True, choices=ActionType.choices)
    description = models.TextField(max_length=16384, blank=True, verbose_name=_("description"))
    on = models.DateTimeField(default=now, verbose_name=_("created on"), db_index=True)
    parameters = models.JSONField()

    priority = models.IntegerField()


def create_rule(repository: Repository, description: str, triggers: List[str], conditions: List[str], actions: List[str]):
    rule = Rule.objects.create(repository=repository, description=description)

    # if no triggers, get them from the variables used in condition expressions
    if not triggers:
        triggers = []
        for condition in conditions:
            parsed = condition.parse_expression()
            for variable in parsed.all_variables:
                for trigger in variable.default_triggers:
                    triggers.append(trigger)

    for trigger_name in triggers:
        Trigger.objects.create(rule=rule, type=TriggerType(trigger_name))

    for expression in conditions:
        Condition.objects.create(rule=rule, description="", expression=expression)

    for idx, action in enumerate(actions):
        Action.objects.create(rule=rule, priority=idx, parameters={}, type=action)


def event_handler(type, data):
    if type == "pr_updated":

        rules = Rule.objects.filter(triggers__type="pr_updated")
        for rule in rules:
            for pull_request in rule.repository.pull_requests:

                context: Context = pull_request.make_context()
                for condition in rule.conditions:
                    if not condition.evaluate(context):
                        # stop processing this rule and go to the next
                        pass

                for action in rule.actions.order_by("priority"):
                    action.execute(context)
# cron
# pr updated
# pr created


# number_reviewers:
# - pr updated
# - pr created

# if number_reviewers > 3
# - add label "lots-of-reviewers"

# rules:
# - conditions:
#   - "number_reviewers>3"
#   actions:
#
#

# triggers:
# - pr updated
# if number_reviewers > 3
# - add label "lots-of-reviewers"