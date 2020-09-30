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
    action = data.get("action")
    tracer.scope_manager.active.span.set_tag("event_name", event_name)
    tracer.scope_manager.active.span.set_tag("action", action)

    installation = installations.get(data.get("installation", {}).get("id"))
    repository_id = _get_repository_id_from_data(data)

    if event_name == "installation" and action == "created":
        on_installation_created(installation, data)

    if not installation:
        logger.error(f"No installation found, skipping event {event_name}")
        return

    if event_name == "installation":
        if action == "deleted":
            installations.delete(installation)
        elif action == "suspended":
            installations.suspend(installation)
    elif event_name == "installation_repositories":
        if action == "added":
            on_repositories_added(installation, data)
        elif action == "removed":
            on_repositories_removed(installation, data)
    elif event_name == "pull_request":
        if action == "opened":
            on_pr_created(installation, repository_id, data["pull_request"])
        elif action == "synchronize":
            on_pr_updated(installation, repository_id, data["pull_request"])
        elif action == "closed":
            on_pr_closed(installation, repository_id, data["pull_request"])
    elif event_name == "push":
        on_push(installation, repository_id, data)
    elif event_name == "check_suite":
        if action == "requested":
            on_check_suite_requested(installation, repository_id, data["check_suite"])
    elif event_name == "check_run":
        app_id = data["check_run"]["check_suite"]["app"]["id"]
        if app_id != settings.GITHUB_APP_ID:
            on_check_run(installation, repository_id, data["check_run"])
    else:
        logger.info(f"Ignored event {event_name}, action {action}")


def _get_repository_id_from_data(data):
    if "repository" in data:
        repository_id = RepositoryIdentifier(data["repository"]["full_name"], remote_id=data["repository"]["id"])
    else:
        repository_id = None
    return repository_id
