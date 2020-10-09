import logging
from typing import Dict
from typing import Optional

from celery import shared_task
from django.conf import settings
from opentracing import tracer

from sleuthpr.models import Installation
from sleuthpr.models import Repository
from sleuthpr.models import RepositoryIdentifier
from sleuthpr.services import installations
from sleuthpr.services import repositories
from sleuthpr.services.github.events import on_check_run
from sleuthpr.services.github.events import on_check_suite_requested
from sleuthpr.services.github.events import on_installation_created
from sleuthpr.services.github.events import on_pr_closed
from sleuthpr.services.github.events import on_pr_created
from sleuthpr.services.github.events import on_pr_reopened
from sleuthpr.services.github.events import on_pr_updated
from sleuthpr.services.github.events import on_pull_request_review
from sleuthpr.services.github.events import on_push
from sleuthpr.services.github.events import on_repositories_added
from sleuthpr.services.github.events import on_repositories_removed
from sleuthpr.services.github.events import on_status

logger = logging.getLogger(__name__)


@shared_task
def event_task(event_name: str, data: Dict, installation: Optional[Installation] = None, **_):
    logger.info(f"GitHub action: {event_name}")
    action = data.get("action")
    tracer.scope_manager.active.span.set_tag("event_name", event_name)
    tracer.scope_manager.active.span.set_tag("action", action)

    if not installation:
        installation_id = data.get("installation", {}).get("id")
        installation = installations.get(installation_id)
    else:
        installation_id = installation.id

    repository = _get_repository(installation, data)

    if event_name == "installation" and action == "created":
        on_installation_created(installation_id, data)
        return

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
            on_pr_created(installation, repository, data["pull_request"])
        elif action == "synchronize":
            on_pr_updated(installation, repository, data["pull_request"])
        elif action == "closed":
            on_pr_closed(installation, repository, data["pull_request"])
        elif action == "reopened":
            on_pr_reopened(installation, repository, data["pull_request"])
        else:
            logger.info(f"Unhandled subevent: {action}")
    elif event_name == "push":
        on_push(installation, repository, data)
    elif event_name == "check_suite":
        if action == "requested":
            on_check_suite_requested(installation, repository, data["check_suite"])
    elif event_name == "check_run":
        app_id = data["check_run"]["check_suite"]["app"]["id"]
        if str(app_id) != settings.GITHUB_APP_ID:
            on_check_run(installation, repository, data["check_run"])
    elif event_name == "status":
        on_status(installation, repository, data)
    elif event_name == "pull_request_review":
        on_pull_request_review(installation, repository, data)
    else:
        logger.info(f"Ignored event {event_name}, action {action}")


def _get_repository(installation, data) -> Optional[Repository]:
    if "repository" in data:
        repository_id = RepositoryIdentifier(data["repository"]["full_name"], remote_id=data["repository"]["id"])
        return repositories.get(installation, repository_id)
    else:
        return None
