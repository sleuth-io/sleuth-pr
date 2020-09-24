from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from typing import Type

from django.db import models
from django.db.models import CASCADE
from django.db.models import TextChoices
from django.utils.timezone import now
from django.utils.translation import gettext_lazy as _
from marshmallow import Schema

from sleuthpr.services import scm
from sleuthpr.services.scm import InstallationClient


@dataclass
class RepositoryIdentifier:
    full_name: str
    remote_id: Optional[str] = None


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
        related_name="repositories",
        verbose_name=_("installation"),
    )
    full_name = models.CharField(max_length=255)
    remote_id = models.CharField(max_length=512, db_index=True, null=True)

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


class TriggerType:
    def __init__(self, key: str, label: str):
        self.key = key
        self.label = label

    def __eq__(self, o: Trigger) -> bool:
        return o.key == self.key


class ActionType:
    def __init__(self, key: str, label: str, parameters: Schema):
        self.key = key
        self.label = label
        self.parameters = parameters

    def __eq__(self, o: Trigger) -> bool:
        return o.key == self.key

    def execute(self, action: Action, target: Any):
        pass


@dataclass
class ConditionVariableType:
    def __init__(self, key: str, label: str, type: Type, default_triggers: List[str]):
        self.key = key
        self.label = label
        self.type = type
        self.default_triggers = default_triggers

    def evaluate(self, target: Any):
        pass


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
    type = models.CharField(max_length=255)


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
