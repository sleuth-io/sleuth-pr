import logging
import os
from datetime import timedelta
from typing import List
from typing import Optional

import jwt
import requests
from django.core.cache import cache
from django.utils.timezone import now
from github import Github
from github import UnknownObjectException

from sleuthpr.models import Installation
from sleuthpr.models import MergeMethod
from sleuthpr.models import RepositoryIdentifier
from sleuthpr.services.scm import CheckDetails
from sleuthpr.services.scm import InstallationClient

logger = logging.getLogger(__name__)


class GitHubInstallationClient(InstallationClient):
    def __init__(self, installation: Installation):
        self.installation = installation

    def get_repositories(self) -> List[RepositoryIdentifier]:
        repos = Github(self._get_installation_token()).get_installation(int(self.installation.remote_id)).get_repos()
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

    def merge(
        self,
        repository: RepositoryIdentifier,
        pr_id: int,
        commit_title: Optional[str],
        commit_message: Optional[str],
        method: MergeMethod,
        sha: str,
    ):
        gh = Github(self._get_installation_token())
        repo = gh.get_repo(repository.full_name, lazy=True)
        repo.get_pull(pr_id).merge(
            commit_title=commit_title,
            commit_message=commit_message,
            merge_method=method.value,
            sha=sha,
        )
        logger.info(f"Merged pr {pr_id}")

    def add_check(
        self,
        repository: RepositoryIdentifier,
        key: str,
        source_sha: str,
        details: CheckDetails,
    ):
        gh = Github(self._get_installation_token())
        repo = gh.get_repo(repository.full_name, lazy=True)
        headers, data = repo._requester.requestJsonAndCheck(
            "POST",
            repo.url + "/check-runs",
            headers={"Accept": "application/vnd.github.antiope-preview+json"},
            input=dict(
                head_sha=source_sha,
                name=key,
                output=dict(title=details.title, summary=details.summary, text=details.body),
                status="completed",
                conclusion="success" if details.success else "failure",
            ),
        )
        logger.info(f"Status check on {source_sha} created for {key}: {details.success}")
        # todo: check response?
        # for pr_data in data["pull_requests"]:
        #     _update_pull_request(repo.installation, repo, pr_data)
        return data["id"]

    def _get_installation_token(self):
        key = f"installation_token.{self.installation.provider}.{self.installation.remote_id}"

        token = cache.get(key)
        if not token:
            jwt_token = _gen_jwt()
            body = {
                "repository_ids": [repo.remote_id for repo in self.installation.repositories.all() if repo.remote_id]
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
