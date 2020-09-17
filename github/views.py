import json
import logging
from datetime import timedelta

import jwt
import requests
from django.shortcuts import render
import os

# Create your views here.

from django.http import HttpResponse
from django.utils.timezone import now
from django.views.decorators.csrf import csrf_exempt

from github.models import Installation, Repository

logger = logging.getLogger(__name__)


def index(request):
    private_key = os.getenv("GITHUB_APP_PRIVATE_KEY")
    return HttpResponse(f"Hello, world. You're at the github app. - {private_key}")


def welcome(request):
    installation_id = request.GET.get("remote_id")
    instance = Installation.objects.get(installation_id=installation_id)

    jwt_token = gen_jwt()
    resp = requests.post(headers={"Authorization": f"Bearer {jwt_token}", "Accept": "application/vnd.github.v3+json"},
                         url=f"https://api.github.com/app/installations/{instance.remote_id}/access_tokens")
    data = resp.json()
    token = data["token"]
    repo = instance.repositories.first()
    resp = requests.get(headers={"Authorization": f"Bearer {token}",
                                 "Accept": "application/vnd.github.v3+json"},
                        url=f"https://api.github.com/repos/{repo.owner}/{repo.name}")
    return HttpResponse(f"Welcome new user! and you can use this token: {resp.json()}")


@csrf_exempt
def event(request):
    event_name = request.headers.get("X-GitHub-Event")
    delivery_id = request.headers.get("X-GitHub-Delivery")

    # todo: validate signature

    body = request.body.decode()
    data = json.loads(body)
    logger.info(f"event: {event_name} body: {body}")

    if event_name == "installation":
        action = data["action"]
        if action == "created":
            installation_id = data["installation"]["id"]
            target_type = data["installation"]["target_type"]
            target_id = data["installation"]["target_id"]
            installation = Installation.objects.create(installation_id=installation_id, target_type=target_type, target_id=target_id)

            for repo_data in data["repositories"]:
                owner, name = repo_data["full_name"].split("/")
                Repository.objects.create(installation=installation, owner=owner, name=name)
                logger.info(f"Registered repo {owner}/{name}")
            # register repositories
            logger.info(f"Created installation {installation_id}")
        elif action == "deleted":
            installation_id = data["installation"]["id"]
            Installation.objects.filter(installation_id=installation_id).delete()
            logger.info("Deleted installation")
    return HttpResponse(f"Event received! - {body}")


@csrf_exempt
def install(request):
    body = request.body.decode()
    return HttpResponse(f"Install event received! - {body}")



def gen_jwt():
    private_key = os.getenv("GITHUB_APP_PRIVATE_KEY").replace("\\n", "\n")
    return jwt.encode(payload={'iat': now(), 'exp': now() + timedelta(minutes=10), 'iss': os.getenv("GITHUB_APP_ID")},
               key=private_key,
               algorithm='RS256').decode()
