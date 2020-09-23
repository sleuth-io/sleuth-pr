import logging
import os

from django.http import HttpResponse

# Create your views here.

logger = logging.getLogger(__name__)


def index(request):
    return HttpResponse(f"Hello, world. You're at the sleuthpr app.")


def welcome(request):
    return HttpResponse(f"Welcome new user!")
