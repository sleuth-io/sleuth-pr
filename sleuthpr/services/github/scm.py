import logging
import os
from datetime import timedelta
from typing import List
from typing import Optional
from typing import Tuple

import jwt
import requests
from django.conf import settings
from django.core.cache import cache
from django.utils.timezone import now
from github import Github
from github import GithubException
from github import UnknownObjectException
from github.PaginatedList import PaginatedList

from sleuthpr.models import CheckStatus
from sleuthpr.models import Installation
from sleuthpr.models import MergeMethod
from sleuthpr.models import PullRequest
from sleuthpr.models import Repository
from sleuthpr.models import RepositoryIdentifier
from sleuthpr.services.github.events import _update_pull_request
from sleuthpr.services.github.events import commit_data_to_commit
from sleuthpr.services.github.events import graphql_commit_data_to_commit
from sleuthpr.services.scm import CheckDetails
from sleuthpr.services.scm import Commit
from sleuthpr.services.scm import InstallationClient
from sleuthpr.services.scm import OperationException

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

    def get_pull_requests(self, repository: Repository) -> List[PullRequest]:
        gh = Github(self._get_installation_token())
        repo = gh.get_repo(repository.full_name, lazy=True)

        def _new_pull_request(_, __, data, *args, **kwargs):
            pr, _ = _update_pull_request(self.installation, repository, data)
            return pr

        result = []
        for pr in PaginatedList(
            _new_pull_request,
            repo._requester,
            repo.url + "/pulls",
            dict(state="open"),
        ):  # type: PullRequest
            result.append(pr)

        logger.info(f"Loaded {len(result)} pull requests")
        return result

    def get_source_url(self, repository: RepositoryIdentifier, path: str) -> str:
        return f"https://github.com/{repository.full_name}/tree/master/{path}"

    def get_pull_request_commits(
        self,
        repository: RepositoryIdentifier,
        pr_id: int,
    ) -> List[Commit]:

        gh = Github(self._get_installation_token())
        repo = gh.get_repo(repository.full_name, lazy=True)

        def _new_commit(_, __, data, *args, **kwargs):
            return commit_data_to_commit(data)

        result = []
        for commit in PaginatedList(
            _new_commit, repo._requester, f"{repo.url}/pulls/{pr_id}/commits", {"per_page": 100}
        ):  # type: Commit
            result.append(commit)

        logger.info(f"Loaded {len(result)} commits")
        return result

    def get_commits(self, repository: Repository, shas: List[str]) -> List[Commit]:
        gh = Github(self._get_installation_token())
        post_parameters = {
            "query": _build_commits_query(repository.identifier, shas),
        }
        headers, data = getattr(gh, "_Github__requester").requestJsonAndCheck(
            "POST", "/graphql", input=post_parameters
        )

        result = []
        for sha in shas:
            cdata = data["data"]["repository"][f"c_{sha}"]
            result.append(graphql_commit_data_to_commit(cdata))

        # todo: handle errors

        logger.info(f"Loaded {len(result)} commits from graphql")
        return result

    def comment_on_pull_request(
        self,
        repository: RepositoryIdentifier,
        pr_id: int,
        sha: str,
        message: str,
    ):
        gh = Github(self._get_installation_token())
        repo = gh.get_repo(repository.full_name, lazy=True)

        post_parameters = {
            "body": message,
            "commit_id": sha,
        }
        headers, data = repo._requester.requestJsonAndCheck("POST", repo.url + "/comments", input=post_parameters)

        # todo: handle response better
        logger.info(f"Pull request commented for {pr_id}")

    def get_statuses(self, repository: RepositoryIdentifier, sha: str) -> List[Tuple[str, CheckStatus]]:
        gh = Github(self._get_installation_token())
        repo = gh.get_repo(repository.full_name, lazy=True)
        result = []

        # hacks necessary to prevent the lib from requesting commits first
        def _new_status(_, __, data, *args, **kwargs):
            return data["context"], CheckStatus(data["state"])

        for status in PaginatedList(
            _new_status,
            repo._requester,
            repo.url + "/commits/" + sha + "/status",
            {"per_page": 100},
            list_item="statuses",
        ):
            logger.info(f"Found {status}")
            result.append(status)

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

        headers, data = repo._requester.requestJsonAndCheck(
            "POST", f"{repo.url}/issues/{pr_id}/labels", input=[label_name]
        )
        logger.info(f"Added label {label_name} to pr {pr_id}")

    def merge(
        self,
        repository: Repository,
        pr_id: int,
        commit_title: Optional[str],
        commit_message: Optional[str],
        method: MergeMethod,
        sha: str,
    ) -> str:
        gh = Github(self._get_installation_token())
        repo = gh.get_repo(repository.identifier.full_name, lazy=True)

        status = repo.get_pull(pr_id).merge(
            commit_title=commit_title,
            commit_message=commit_message,
            merge_method=method.value,
            sha=sha,
        )
        logger.info(f"Merged pr {pr_id}")
        return status.sha

    def update_pull_request(
        self,
        repository: Repository,
        pr_id: int,
        sha: str,
    ):

        gh = Github(self._get_installation_token())
        repo = gh.get_repo(repository.full_name, lazy=True)
        try:
            headers, data = repo._requester.requestJsonAndCheck(
                "PUT",
                f"{repo.url}/pulls/{pr_id}/update-branch",
                headers={"Accept": "application/vnd.github.lydian-preview+json"},
                input=dict(
                    expected_head_sha=sha,
                ),
            )
            # todo: handle response better
            logger.info(f"Pull request being updated")
        except GithubException as ex:
            raise OperationException(ex.data.get("message"))

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
            headers={"Accept": "application/vnd.github.v3+json"},
            input=dict(
                head_sha=source_sha,
                name=key,
                output=dict(title=details.title, summary=details.summary, text=details.body),
                status="completed",
                conclusion=self._status_to_check_conclusion(details),
            ),
        )
        logger.info(f"Status check on {source_sha} created for {key}: {details.status}")
        # todo: check response?
        # for pr_data in data["pull_requests"]:
        #     _update_pull_request(repo.installation, repo, pr_data)
        return data["id"]

    @staticmethod
    def _status_to_check_conclusion(details):
        if details.status == CheckStatus.SUCCESS:
            conclusion = "success"
        elif details.status == CheckStatus.FAILURE:
            conclusion = "failure"
        else:
            conclusion = "neutral"
        return conclusion

    def update_check(
        self,
        repository: RepositoryIdentifier,
        key: str,
        source_sha: str,
        details: CheckDetails,
        remote_check_id: str,
    ):
        gh = Github(self._get_installation_token())
        repo = gh.get_repo(repository.full_name, lazy=True)
        headers, data = repo._requester.requestJsonAndCheck(
            "PATCH",
            repo.url + f"/check-runs/{remote_check_id}",
            headers={"Accept": "application/vnd.github.v3+json"},
            input=dict(
                head_sha=source_sha,
                name=key,
                output=dict(title=details.title, summary=details.summary, text=details.body),
                status="completed",
                conclusion=self._status_to_check_conclusion(details),
            ),
        )
        logger.info(f"Status check on {source_sha} updated for {key}: {details.status}")
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


class GitHubActionInstallationClient(GitHubInstallationClient):
    def _get_installation_token(self):
        return settings.GITHUB_TOKEN


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


def _build_commits_query(repo: RepositoryIdentifier, commit_shas: List[str]) -> str:
    commit_queries = []
    for sha in commit_shas:
        commit_queries.append(
            f"""
            c_{sha}: object(oid: "{sha}") {{
              ... on Commit {{
                oid
                message
                author {{
                  name
                  email
                }}
                committer {{
                  name
                  email
                }}
                parents(first:100) {{
                  edges {{
                    node {{
                      ... on Commit {{
                        oid
                      }}
                    }}
                  }}
                }}
              }}
            }}"""
        )

    joined_commit_queries = "\n".join(commit_queries)
    query = f"""
    {{
        repository(owner: "{repo.owner}", name: "{repo.name}")
        {{
            {joined_commit_queries}
        }}
    }}
    """
    return query
