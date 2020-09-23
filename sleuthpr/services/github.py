import json
import logging
import os
from datetime import timedelta
from typing import List
from typing import Optional

import jwt
import requests
from django.core.cache import cache
from django.http import HttpResponse
from django.utils.timezone import now
from django.views.decorators.csrf import csrf_exempt
from github import Github
from github import UnknownObjectException

from sleuthpr.models import Installation
from sleuthpr.models import RepositoryIdentifier
from sleuthpr.services import installations
from sleuthpr.services import repositories
from sleuthpr.services.scm import InstallationClient

logger = logging.getLogger(__name__)


@csrf_exempt
def on_event(request):
    event_name = request.headers.get("X-GitHub-Event")
    delivery_id = request.headers.get("X-GitHub-Delivery")

    # todo: validate signature

    body = request.body.decode()
    data = json.loads(body)
    logger.info(f"event: {event_name} body: {body}")

    if event_name == "installation":
        action = data["action"]
        remote_id = data["installation_id"]
        if action == "created":
            on_installation_created(remote_id, data)
        elif action == "deleted":
            installations.delete(remote_id)
        elif action == "suspended":
            installations.suspend(remote_id)
    elif event_name == "installation_repositories":
        action = data["action"]
        remote_id = data["installation"]["id"]
        if action == "added":
            on_repositories_added(remote_id, data)
        elif action == "removed":
            on_repositories_removed(remote_id, data)

    return HttpResponse(f"Event received! - {body}")


def on_repositories_added(installation_id, data):
    installation = installations.get(installation_id)
    if data["repository_selection"] == "all":
        repos = installation.client.get_repositories()
        repositories.set_repositories(installation, repos)
    else:
        repos = [
            RepositoryIdentifier(full_name=repo["full_name"])
            for repo in data["repositories_added"]
        ]
        repositories.add(installation, repos)


def on_repositories_removed(installation_id, data):
    installation = installations.get(installation_id)
    if data["repository_selection"] == "all":
        repos = installation.client.get_repositories()
        repositories.set_repositories(installation, repos)
    else:
        repos = [
            RepositoryIdentifier(full_name=repo["full_name"])
            for repo in data["repositories_removed"]
        ]
        repositories.remove(installation, repos)


def on_installation_created(installation_id, data):
    target_type = data["installation"]["target_type"]
    target_id = data["installation"]["target_id"]
    repos = [
        RepositoryIdentifier(full_name=repo["full_name"])
        for repo in data["repositories"]
    ]
    installations.create(
        remote_id=installation_id,
        target_type=target_type,
        target_id=target_id,
        repository_ids=repos,
    )


class GitHubInstallationClient(InstallationClient):
    def __init__(self, installation: Installation):
        self.installation = installation

    def get_repositories(self) -> List[RepositoryIdentifier]:
        repos = (
            Github(self._get_installation_token())
            .get_installation(int(self.installation.remote_id))
            .get_repos()
        )
        result: List[RepositoryIdentifier] = []
        for repo in repos:
            if repo.permissions.push:
                result.append(RepositoryIdentifier(full_name=repo.full_name))

        return result

    def get_content(self, repository: RepositoryIdentifier, path: str) -> Optional[str]:

        gh = Github(self._get_installation_token())
        repo = gh.get_repo(repository.full_name, lazy=True)
        try:
            return repo.get_contents(path).content
        except UnknownObjectException:
            return None

    def _get_installation_token(self):
        key = f"installation_token.{self.installation.provider}.{self.installation.remote_id}"

        token = cache.get(key)
        if not token:
            jwt_token = _gen_jwt()
            resp = requests.post(
                headers={
                    "Authorization": f"Bearer {jwt_token}",
                    "Accept": "application/vnd.sleuthpr.v3+json",
                },
                url=f"https://api.github.com/app/installations/{self.installation.remote_id}/access_tokens",
            )
            data = resp.json()
            token = data["token"]
            cache.set(key, token, timeout=50)
        return token


def _gen_jwt():
    private_key = os.getenv("GITHUB_APP_PRIVATE_KEY").replace("\\n", "\n")
    return jwt.encode(
        payload={
            "iat": now(),
            "exp": now() + timedelta(minutes=10),
            "iss": os.getenv("GITHUB_APP_ID"),
        },
        key=private_key,
        algorithm="RS256",
    ).decode()
