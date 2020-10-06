# pylint: disable=wildcard-import
import os

from .base import *  # noqa


ENVIRONMENT = "github_action"

CELERY_TASK_ALWAYS_EAGER = True

LOGGING["root"]["level"] = "INFO"  # noqa

GITHUB_TOKEN = os.environ["GITHUB_TOKEN"]
