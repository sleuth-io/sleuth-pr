# pylint: disable=wildcard-import
from .base import *  # noqa


ENVIRONMENT = "github_action"

CELERY_TASK_ALWAYS_EAGER = True

LOGGING["root"]["level"] = "INFO"  # noqa
