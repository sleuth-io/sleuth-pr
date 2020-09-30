import logging
from typing import Dict

from celery import shared_task
from django.conf import settings
from opentracing import tracer

from sleuthpr.models import RepositoryIdentifier
from sleuthpr.services import installations
from sleuthpr.services.github.events import on_check_run
from sleuthpr.services.github.events import on_check_suite_requested
from sleuthpr.services.github.events import on_installation_created
from sleuthpr.services.github.events import on_pr_closed
from sleuthpr.services.github.events import on_pr_created
from sleuthpr.services.github.events import on_pr_updated
from sleuthpr.services.github.events import on_push
from sleuthpr.services.github.events import on_repositories_added
from sleuthpr.services.github.events import on_repositories_removed

logger = logging.getLogger(__name__)


@shared_task
def event_task(event_name: str, data: Dict, **kwargs):
    logger.info(f"GitHub action: {event_name}")
    tracer.scope_manager.active.span.set_tag("event_name", event_name)
    if event_name == "installation":
        action = data["action"]
        remote_id = data["installation"]["id"]
        if action == "created":
            on_installation_created(remote_id, data)
        elif action == "deleted":
            installations.delete(remote_id)
        elif action == "suspended":
            installations.suspend(remote_id)
    elif event_name == "installation_repositories":
        action = data["action"]
        remote_id = data["installation"]["id"]
        if action == "added":
            on_repositories_added(remote_id, data)
        elif action == "removed":
            on_repositories_removed(remote_id, data)
    elif event_name == "pull_request":
        action = data["action"]
        repository_id = RepositoryIdentifier(data["repository"]["full_name"], remote_id=data["repository"]["id"])
        remote_id = data["installation"]["id"]
        if action == "opened":
            on_pr_created(remote_id, repository_id, data["pull_request"])
        elif action == "synchronize":
            on_pr_updated(remote_id, repository_id, data["pull_request"])
        elif action == "closed":
            on_pr_closed(remote_id, repository_id, data["pull_request"])
    elif event_name == "push":
        repository_id = RepositoryIdentifier(data["repository"]["full_name"], remote_id=data["repository"]["id"])
        remote_id = data["installation"]["id"]
        on_push(remote_id, repository_id, data)
    elif event_name == "check_suite":
        action = data["action"]
        repository_id = RepositoryIdentifier(data["repository"]["full_name"], remote_id=data["repository"]["id"])
        remote_id = data["installation"]["id"]
        if action == "requested":
            on_check_suite_requested(remote_id, repository_id, data["check_suite"])
    elif event_name == "check_run":
        app_id = data["check_run"]["check_suite"]["app"]["id"]
        if app_id != settings.GITHUB_APP_ID:
            repository_id = RepositoryIdentifier(data["repository"]["full_name"], remote_id=data["repository"]["id"])
            remote_id = data["installation"]["id"]
            on_check_run(remote_id, repository_id, data["check_run"])
    else:
        logger.info(f"Ignored event {event_name}")
