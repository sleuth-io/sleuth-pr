import json
import logging
import os

from django.conf import settings
from django.core.management.base import BaseCommand

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Process a github action"

    def add_arguments(self, parser):
        pass

    def handle(self, *args, **options):

        event_name = os.environ["GITHUB_EVENT_NAME"]
        event_path = os.environ["GITHUB_EVENT_PATH"]
        event_data = json.load(open(event_path))

        logger.info(f"Environment: {settings.ENVIRONMENT}")
        logger.info(f"event: {event_name}: body: {event_data}")

        # event_task(event_name, event_data)
