# pylint: disable=wildcard-import
from .base import *  # noqa


ENVIRONMENT = "test"

DEBUG = False

CELERY_TASK_ALWAYS_EAGER = True

LOGGING["root"]["level"] = "DEBUG"  # noqa
