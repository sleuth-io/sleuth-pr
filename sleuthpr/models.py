from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from typing import Callable
from typing import Dict
from typing import List
from typing import Optional
from typing import Type

from django.db import models
from django.db.models import CASCADE
from django.db.models import SET_NULL
from django.db.models import TextChoices
from django.utils.timezone import now
from django.utils.translation import gettext_lazy as _
from marshmallow import Schema

from sleuthpr.services import scm
from sleuthpr.services.scm import InstallationClient


# pylint: disable=W0622


class MergeMethod(TextChoices):
    REBASE = ("rebase", "Rebase")
    SQUASH = ("squash", "Squash")
    MERGE = ("merge", "Merge commit")


@dataclass
class RepositoryIdentifier:
    full_name: str
    remote_id: Optional[str] = None


class Provider(TextChoices):
    GITHUB = ("github", "GitHub")
    GITLAB = ("gitlab", "GitLab")
    BITBUCKET = ("bitbucket", "Bitbucket")


class CheckStatus(TextChoices):
    SUCCESS = ("success", "Success")
    FAILURE = ("failure", "Failure")
    PENDING = ("pending", "Pending")
    ERROR = ("error", "Error")


class TriState(TextChoices):
    TRUE = ("true", "True")
    FALSE = ("false", "False")
    UNKNOWN = ("unknown", "Unknown")

    @classmethod
    def from_bool(cls, value: Optional[bool, None]) -> TriState:
        if value:
            return cls.TRUE
        elif value is None:
            return cls.UNKNOWN
        else:
            return cls.FALSE

    def to_bool(self) -> bool:
        return self == TriState.TRUE

    def __bool__(self):
        return self == self.TRUE


class ReviewState(TextChoices):
    APPROVED = ("approved", "Approved")
    DISMISSED = ("dismissed", "Dismissed")
    CHANGES_REQUESTED = ("changes_requested", "Changes requested")
    COMMENTED = ("commented", "Commented")
    PENDING = ("pending", "Pending")


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

    @property
    def ordered_rules(self):
        return self.rules.order_by("order").all()

    def source_url(self, path: str):
        return self.installation.client.get_source_url(self.identifier, path)


class ExternalUser(models.Model):
    name = models.CharField(max_length=512, verbose_name=_("name"), null=True, db_index=True)
    email = models.EmailField(max_length=512, verbose_name=_("email"), null=True, db_index=True)
    username = models.CharField(max_length=512, null=True, verbose_name=_("username"), db_index=True)
    remote_id = models.CharField(max_length=512, null=True, verbose_name=_("uid"), db_index=True)

    installation = models.CharField(max_length=255, verbose_name=_("provider"), db_index=True)


class RepositoryBranch(models.Model):
    name = models.CharField(max_length=255, verbose_name=_("name"), db_index=True)
    head_sha = models.CharField(max_length=1024, verbose_name=_("head sha"), db_index=True)
    repository = models.ForeignKey(
        Repository,
        on_delete=CASCADE,
        related_name="branches",
        verbose_name=_("repository"),
    )


class PullRequest(models.Model):
    title = models.TextField(default="", max_length=16384, verbose_name=_("title"), db_index=True)
    description = models.TextField(max_length=16384, blank=True, verbose_name=_("description"))
    on = models.DateTimeField(default=now, verbose_name=_("created on"), db_index=True)
    remote_id = models.CharField(max_length=512, db_index=True)
    source_branch_name = models.CharField(
        max_length=1024,
        blank=True,
        null=True,
        verbose_name=_("source branch name"),
        db_index=True,
    )
    source_sha = models.CharField(
        max_length=1024,
        blank=True,
        null=True,
        verbose_name=_("source sha"),
        db_index=True,
    )
    base_branch_name = models.CharField(
        max_length=1024,
        blank=True,
        null=True,
        verbose_name=_("base branch name"),
        db_index=True,
    )
    base_sha = models.CharField(
        max_length=1024,
        blank=True,
        null=True,
        verbose_name=_("base sha"),
        db_index=True,
    )
    url = models.URLField(max_length=1024, blank=True, null=True, verbose_name=_("url"))
    repository = models.ForeignKey(
        Repository,
        on_delete=CASCADE,
        related_name="pull_requests",
        verbose_name=_("repository"),
    )
    author = models.ForeignKey(
        ExternalUser,
        related_name="authored_pull_requests",
        verbose_name=_("author"),
        on_delete=SET_NULL,
        null=True,
    )
    draft = models.BooleanField(default=False)
    merged = models.BooleanField(default=False)
    mergeable = models.CharField(max_length=15, choices=TriState.choices, default=TriState.UNKNOWN)
    rebaseable = models.CharField(max_length=15, choices=TriState.choices, default=TriState.UNKNOWN)
    conflict = models.CharField(max_length=15, choices=TriState.choices, default=TriState.UNKNOWN)
    status = models.CharField(max_length=128, blank=True, null=True, verbose_name=_("status"))

    @property
    def source_commit(self) -> Optional[RepositoryCommit]:
        return self.repository.commits.get(sha=self.source_sha) if self.source_sha else None

    @property
    def base_commit(self) -> Optional[RepositoryCommit]:
        return self.repository.commits.get(sha=self.base_sha) if self.base_sha else None


class PullRequestAssignee(models.Model):
    user = models.ForeignKey(
        ExternalUser,
        related_name="assigned_pull_requests",
        verbose_name=_("user"),
        on_delete=CASCADE,
    )

    pull_request = models.ForeignKey(
        PullRequest,
        related_name="assignees",
        verbose_name=_("pull_request"),
        null=True,
        on_delete=CASCADE,
    )


class PullRequestReviewer(models.Model):
    user = models.ForeignKey(
        ExternalUser,
        related_name="reviewer_for_pull_requests",
        verbose_name=_("user"),
        on_delete=CASCADE,
    )

    pull_request = models.ForeignKey(
        PullRequest,
        related_name="reviewers",
        verbose_name=_("pull_request"),
        on_delete=CASCADE,
    )
    state = models.CharField(
        max_length=20,
        verbose_name=_("state"),
        db_index=True,
        choices=ReviewState.choices,
        default=ReviewState.PENDING,
    )


class PullRequestLabel(models.Model):
    value = models.CharField(max_length=255, verbose_name=_("value"), db_index=True)
    pull_request = models.ForeignKey(
        PullRequest,
        related_name="labels",
        verbose_name=_("pull_request"),
        on_delete=CASCADE,
    )


class PullRequestStatus(models.Model):
    state = models.CharField(max_length=20, verbose_name=_("state"), db_index=True, choices=CheckStatus.choices)
    context = models.CharField(max_length=255, verbose_name=_("context"), db_index=True)
    pull_request = models.ForeignKey(
        PullRequest,
        related_name="statuses",
        verbose_name=_("pull_request"),
        on_delete=CASCADE,
    )


class RepositoryCommit(models.Model):
    class Meta:
        unique_together = (
            "repository",
            "sha",
        )

    sha = models.CharField(max_length=1024, verbose_name=_("sha"), db_index=True)
    message = models.TextField(max_length=16384, null=True, blank=True, verbose_name=_("message"))
    repository = models.ForeignKey(
        Repository,
        on_delete=CASCADE,
        related_name="commits",
        verbose_name=_("repository"),
    )

    author = models.ForeignKey(
        ExternalUser,
        related_name="authored_commits",
        verbose_name=_("author"),
        on_delete=SET_NULL,
        null=True,
    )

    committer = models.ForeignKey(
        ExternalUser,
        related_name="committers",
        verbose_name=_("committer"),
        on_delete=SET_NULL,
        null=True,
    )

    pull_request = models.ForeignKey(
        PullRequest,
        related_name="commits",
        verbose_name=_("pull_request"),
        null=True,
        on_delete=SET_NULL,
    )
    # fixme: this should be the commit date
    on = models.DateTimeField(default=now, verbose_name=_("created on"), db_index=True)


class RepositoryCommitParent(models.Model):
    repository = models.ForeignKey(
        Repository,
        on_delete=CASCADE,
        related_name="commit_tree",
        verbose_name=_("repository"),
    )

    parent = models.ForeignKey(
        RepositoryCommit,
        on_delete=CASCADE,
        related_name="children",
        verbose_name=_("parent"),
    )
    child = models.ForeignKey(
        RepositoryCommit,
        on_delete=CASCADE,
        related_name="parents",
        verbose_name=_("child"),
    )


class Rule(models.Model):
    title = models.CharField(default="", max_length=255, verbose_name=_("title"), db_index=True)
    description = models.TextField(max_length=16384, blank=True, verbose_name=_("description"))
    on = models.DateTimeField(default=now, verbose_name=_("created on"), db_index=True)
    line_number = models.IntegerField(default=-1)
    repository = models.ForeignKey(
        Repository,
        on_delete=CASCADE,
        related_name="rules",
        verbose_name=_("repository"),
    )
    order = models.IntegerField()

    @property
    def ordered_conditions(self):
        return self.conditions.order_by("order").all()

    @property
    def ordered_actions(self):
        return self.actions.order_by("order").all()


class TriggerType:
    def __init__(self, key: str, label: str):
        self.key = key
        self.label = label

    def __eq__(self, o: Trigger) -> bool:
        return o.key == self.key


class ActionType:
    def __init__(self, key: str, label: str, parameters: Schema, conditions: List[str] = None):
        self.key = key
        self.label = label
        self.parameters = parameters
        self.conditions = conditions if conditions is not None else []

    def __eq__(self, o: Trigger) -> bool:
        return o.key == self.key

    def execute(self, action: Action, context: Dict) -> bool:
        pass


@dataclass
class ConditionVariableType:
    def __init__(
        self,
        key: str,
        label: str,
        type: Type,
        default_triggers: List[TriggerType],
        evaluate: Optional[Callable[[Dict], Any]] = None,
    ):
        self.key = key
        self.label = label
        self.type = type
        self.default_triggers = default_triggers
        self._evaluate = evaluate

    def __call__(self, context: Dict):
        if self._evaluate:
            return self._evaluate(context)


class Trigger(models.Model):
    rule = models.ForeignKey(
        Rule,
        on_delete=CASCADE,
        related_name="triggers",
        verbose_name=_("installation"),
    )
    type = models.CharField(max_length=255)
    description = models.TextField(max_length=16384, blank=True, default="", verbose_name=_("description"))
    line_number = models.IntegerField(default=-1)


class Condition(models.Model):
    description = models.TextField(max_length=16384, blank=True, verbose_name=_("description"))
    expression = models.TextField(max_length=16384, blank=True, verbose_name=_("expression"))
    on = models.DateTimeField(default=now, verbose_name=_("created on"), db_index=True)
    line_number = models.IntegerField(default=-1)
    rule = models.ForeignKey(
        Rule,
        on_delete=CASCADE,
        related_name="conditions",
        verbose_name=_("rule"),
    )
    order = models.IntegerField()


class RuleCheckRun(models.Model):
    rule = models.ForeignKey(
        Rule,
        related_name="checks",
        verbose_name=_("rule"),
        null=True,
        on_delete=CASCADE,
    )

    pull_request = models.ForeignKey(
        PullRequest,
        related_name="checks",
        verbose_name=_("pull_request"),
        null=True,
        on_delete=CASCADE,
    )

    status = models.CharField(max_length=50, db_index=True, choices=CheckStatus.choices)

    remote_id = models.CharField(max_length=512, db_index=True)


class Action(models.Model):
    type = models.CharField(
        max_length=255,
        verbose_name=_("type"),
        db_index=True,
    )
    description = models.TextField(max_length=16384, blank=True, verbose_name=_("description"))
    on = models.DateTimeField(default=now, verbose_name=_("created on"), db_index=True)
    parameters = models.JSONField()
    line_number = models.IntegerField(default=-1)
    rule = models.ForeignKey(
        Rule,
        on_delete=CASCADE,
        related_name="actions",
        verbose_name=_("rule"),
    )
    order = models.IntegerField()


class ActionResult(models.Model):
    action = models.ForeignKey(
        Action,
        on_delete=CASCADE,
        related_name="results",
        verbose_name=_("action"),
    )
    commit = models.ForeignKey(
        RepositoryCommit,
        on_delete=CASCADE,
        related_name="actions_results",
        verbose_name=_("commit"),
    )
    status = models.CharField(max_length=50, db_index=True, choices=CheckStatus.choices)
    message = models.TextField(max_length=16384, blank=True, verbose_name=_("message"))
    on = models.DateTimeField(default=now, verbose_name=_("created on"), db_index=True)
