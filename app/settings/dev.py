# pylint: disable=wildcard-import
from .base import *  # noqa

ENVIRONMENT = "dev"

DEBUG = True

ALLOWED_HOSTS = ["pr-dev.ngrok.io"]

CELERY_TASK_ALWAYS_EAGER = True

LOGGING["root"]["level"] = "DEBUG"  # noqa
