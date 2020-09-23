from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Dict
from typing import List

from django.db import models
from django.db.models import CASCADE
from django.db.models import TextChoices
from django.utils.timezone import now
from django.utils.translation import gettext_lazy as _

from sleuthpr.services import scm
from sleuthpr.services.scm import InstallationClient


@dataclass
class RepositoryIdentifier:
    full_name: str


class Provider(TextChoices):
    GITHUB = ("github", "GitHub")
    GITLAB = ("gitlab", "GitLab")
    BITBUCKET = ("bitbucket", "Bitbucket")


class Installation(models.Model):
    # remote identifier for this installation
    remote_id = models.CharField(max_length=512, db_index=True)

    # remote type the installation is for, i.e. github org or github user
    target_type = models.CharField(max_length=50)

    # remote identifier for the target
    target_id = models.CharField(max_length=255)
    on = models.DateTimeField(default=now, verbose_name=_("created on"), db_index=True)
    provider = models.CharField(max_length=50, choices=Provider.choices)
    active = models.BooleanField(default=True)

    @property
    def client(self) -> InstallationClient:
        return scm.get_client(self)


class Repository(models.Model):
    installation = models.ForeignKey(
        Installation,
        on_delete=CASCADE,
        related_name="repository_ids",
        verbose_name=_("installation"),
    )
    full_name = models.CharField(max_length=255)

    @property
    def identifier(self):
        return RepositoryIdentifier(full_name=self.full_name)


class ExternalUser(models.Model):
    name = models.CharField(max_length=512, verbose_name=_("name"), db_index=True)
    email = models.EmailField(
        max_length=512, verbose_name=_("email"), blank=True, db_index=True
    )
    username = models.CharField(
        max_length=512, blank=True, verbose_name=_("username"), db_index=True
    )
    remote_id = models.CharField(
        max_length=512, blank=True, null=True, verbose_name=_("uid"), db_index=True
    )

    installation = models.CharField(
        max_length=255, verbose_name=_("provider"), db_index=True
    )


class PullRequest(models.Model):
    title = models.TextField(
        default="", max_length=16384, verbose_name=_("title"), db_index=True
    )
    description = models.TextField(
        max_length=16384, blank=True, verbose_name=_("description")
    )
    on = models.DateTimeField(default=now, verbose_name=_("created on"), db_index=True)
    remote_id = models.CharField(max_length=512, db_index=True)
    source_branch_name = models.CharField(
        max_length=1024,
        blank=True,
        null=True,
        verbose_name=_("source branch name"),
        db_index=True,
    )
    url = models.URLField(max_length=1024, blank=True, verbose_name=_("url"))
    repository = models.ForeignKey(
        Repository,
        on_delete=CASCADE,
        related_name="pull_requests",
        verbose_name=_("repository"),
    )


class Rule(models.Model):
    title = models.CharField(
        default="", max_length=255, verbose_name=_("title"), db_index=True
    )
    description = models.TextField(
        max_length=16384, blank=True, verbose_name=_("description")
    )
    on = models.DateTimeField(default=now, verbose_name=_("created on"), db_index=True)
    repository = models.ForeignKey(
        Repository,
        on_delete=CASCADE,
        related_name="rules",
        verbose_name=_("repository"),
    )
    order = models.IntegerField()


class TriggerType(TextChoices):
    PR_UPDATED = ("pr_updated", "PR Updated")
    PR_CREATED = ("pr_created", "PR Created")
    CRON_5_MINUTES = ("cron", "Every 5 minutes")


class ActionType(TextChoices):
    MERGE = ("pr_merge", "PR Merge")
    CLOSE = ("pr_close", "PR Close")
    ADD_LABEL = ("add_label", "Add Label")

    def execute(self, context: Dict):
        pass


@dataclass
class ConditionVariable:
    key: str
    title: str

    default_triggers: List[TriggerType]


CONDITION_VARIABLES = {
    "number_reviewers": ConditionVariable(
        key="number_reviewers",
        title="Number of reviewers",
        default_triggers=[TriggerType.PR_CREATED, TriggerType.PR_UPDATED],
    )
}


class Context:
    pull_request: PullRequest
    repository: Repository
    installation: Installation


class Trigger(models.Model):
    rule = models.ForeignKey(
        Rule,
        on_delete=CASCADE,
        related_name="triggers",
        verbose_name=_("installation"),
    )
    type = models.CharField(max_length=30, choices=TriggerType.choices)


class Condition(models.Model):
    description = models.TextField(
        max_length=16384, blank=True, verbose_name=_("description")
    )
    expression = models.TextField(
        max_length=16384, blank=True, verbose_name=_("expression")
    )
    on = models.DateTimeField(default=now, verbose_name=_("created on"), db_index=True)
    rule = models.ForeignKey(
        Rule,
        on_delete=CASCADE,
        related_name="conditions",
        verbose_name=_("rule"),
    )
    order = models.IntegerField()


class Action(models.Model):
    type = models.CharField(
        max_length=255,
        verbose_name=_("type"),
        db_index=True,
        choices=ActionType.choices,
    )
    description = models.TextField(
        max_length=16384, blank=True, verbose_name=_("description")
    )
    on = models.DateTimeField(default=now, verbose_name=_("created on"), db_index=True)
    parameters = models.JSONField()
    rule = models.ForeignKey(
        Rule,
        on_delete=CASCADE,
        related_name="actions",
        verbose_name=_("rule"),
    )
    order = models.IntegerField()


def create_rule(
    repository: Repository,
    description: str,
    triggers: List[str],
    conditions: List[str],
    actions: List[str],
):
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
