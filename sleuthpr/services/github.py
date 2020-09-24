import json
import logging
import os
from datetime import timedelta
from typing import Dict
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
from sleuthpr.models import PullRequest
from sleuthpr.models import RepositoryIdentifier
from sleuthpr.services import installations
from sleuthpr.services import pull_requests
from sleuthpr.services import repositories
from sleuthpr.services import rules
from sleuthpr.services.scm import InstallationClient
from sleuthpr.sleuthpr import PR_CREATED
from sleuthpr.sleuthpr import PR_UPDATED

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
        remote_id = data["installation"]["id"]
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
    elif event_name == "pull_request":
        action = data["action"]
        repository_id = RepositoryIdentifier(
            data["repository"]["full_name"], remote_id=data["repository"]["id"]
        )
        remote_id = data["installation"]["id"]
        if action == "opened":
            on_pr_created(remote_id, repository_id, data["pull_request"])
        elif action == "synchronize":
            on_pr_updated(remote_id, repository_id, data["pull_request"])
    elif event_name == "push":
        repository_id = RepositoryIdentifier(
            data["repository"]["full_name"], remote_id=data["repository"]["id"]
        )
        remote_id = data["installation"]["id"]
        on_push(remote_id, repository_id, data)
    else:
        logger.info(f"Ignored event {event_name}")

    return HttpResponse(f"Event received! - {body}")


def on_push(remote_id: str, repository_id: RepositoryIdentifier, data: Dict):
    if "refs/heads/master" == data["ref"]:
        installation = installations.get(remote_id)
        repo = installation.repositories.filter(
            full_name=repository_id.full_name
        ).first()
        files = {}
        for commit in data["commits"]:
            for action in ("modified", "added", "removed"):
                for file in commit[action]:
                    files[file] = action

        if files.get(".sleuth/rules.yml"):
            logger.info("Push contained a rules file change, refreshing")
            repositories.refresh_rules(installation, repo)

        logger.info("Got a master push")
    else:
        logger.info("Not a master push")


def on_pr_created(remote_id: str, repository_id: RepositoryIdentifier, pr_data: Dict):
    installation = installations.get(remote_id)
    repo = installation.repositories.filter(full_name=repository_id.full_name).first()
    pr = pull_requests.update(installation, repo, pr_data)
    rules.evaluate(repo, PR_CREATED, {"pull_request": pr})


def on_pr_updated(remote_id: str, repository_id: RepositoryIdentifier, pr_data: Dict):
    installation = installations.get(remote_id)
    repo = installation.repositories.filter(full_name=repository_id.full_name).first()
    pr = pull_requests.update(installation, repo, pr_data)
    rules.evaluate(repo, PR_UPDATED, {"pull_request": pr})


def on_repositories_added(installation_id, data):
    installation = installations.get(installation_id)
    if data["repository_selection"] == "all":
        repos = installation.client.get_repositories()
        repositories.set_repositories(installation, repos)
    else:
        repos = [
            RepositoryIdentifier(full_name=repo["full_name"], remote_id=repo["id"])
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
            RepositoryIdentifier(full_name=repo["full_name"], remote_id=repo["id"])
            for repo in data["repositories_removed"]
        ]
        repositories.remove(installation, repos)


def on_installation_created(installation_id, data):
    target_type = data["installation"]["target_type"]
    target_id = data["installation"]["target_id"]
    repos = [
        RepositoryIdentifier(full_name=repo["full_name"], remote_id=repo["id"])
        for repo in data["repositories"]
    ]
    installations.create(
        remote_id=installation_id,
        target_type=target_type,
        target_id=target_id,
        repository_ids=repos,
        provider="github",
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
            return repo.get_contents(path).decoded_content.decode("utf8")
        except UnknownObjectException:
            return None

    def add_label(self, repository: RepositoryIdentifier, pr_id: int, label_name: str):
        gh = Github(self._get_installation_token())
        repo = gh.get_repo(repository.full_name, lazy=True)
        repo.get_pull(pr_id).add_to_labels(label_name)
        logger.info(f"Added label {label_name} to pr {pr_id}")

    def _get_installation_token(self):
        key = f"installation_token.{self.installation.provider}.{self.installation.remote_id}"

        token = cache.get(key)
        if not token:
            jwt_token = _gen_jwt()
            body = {
                "repository_ids": [
                    repo.remote_id
                    for repo in self.installation.repositories.all()
                    if repo.remote_id
                ]
            }
            resp = requests.post(
                headers={
                    "Authorization": f"Bearer {jwt_token}",
                    "Accept": "application/vnd.github.v3+json,application/json",
                },
                url=f"https://api.github.com/app/installations/{self.installation.remote_id}/access_tokens",
                json=body,
            )
            if resp.status_code < 299:
                data = resp.json()

                token = data["token"]
                cache.set(key, token, timeout=50)
            else:
                logger.error(f"Unable to get token: {resp.text}")
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
