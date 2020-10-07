import json
import logging
import os

from django.conf import settings
from django.core.management.base import BaseCommand
from opentracing import tracer

from sleuthpr.models import RepositoryIdentifier
from sleuthpr.services import installations
from sleuthpr.services.github.tasks import event_task

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Process a github action"

    def add_arguments(self, parser):
        pass

    def handle(self, *args, **options):

        event_name = os.environ["GITHUB_EVENT_NAME"]
        event_path = os.environ["GITHUB_EVENT_PATH"]
        event_data = json.load(open(event_path))

        with tracer.start_active_span("action", finish_on_close=True):
            repo = event_data["repository"]
            repos = [RepositoryIdentifier(full_name=repo["full_name"], remote_id=repo["id"])]
            installation = installations.create(
                remote_id="1",
                target_type="github_action",
                target_id="1",
                repository_ids=repos,
                provider="github_action",
            )

            logger.info(f"Environment: {settings.ENVIRONMENT}")
            logger.info(f"event: {event_name}: body: {event_data}")

            event_task(event_name, event_data, installation=installation)
