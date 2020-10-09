from __future__ import annotations

from dataclasses import dataclass
from typing import List
from typing import Optional
from typing import Tuple
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sleuthpr.models import (
        Installation,
        RepositoryIdentifier,
        MergeMethod,
        PullRequest,
        Repository,
        CheckStatus,
    )


@dataclass
class CheckDetails:
    title: str
    summary: str
    body: str
    success: bool


@dataclass
class Commit:
    sha: str
    message: str
    author_name: str
    author_email: str
    committer_name: str
    committer_email: str
    parents: List[str]


def get_client(installation: Installation):
    if installation.provider == "github":
        from sleuthpr.services.github import GitHubInstallationClient

        return GitHubInstallationClient(installation)
    elif installation.provider == "github_action":
        from sleuthpr.services.github import GitHubActionInstallationClient

        return GitHubActionInstallationClient(installation)
    else:
        raise ValueError(f"Unsupported provider: {installation.provider}")


class OperationException(Exception):
    pass


class InstallationClient:
    def get_repositories(self) -> List[RepositoryIdentifier]:
        pass

    def get_content(self, repository: RepositoryIdentifier, path: str) -> Optional[str]:
        pass

    def add_label(self, repository: RepositoryIdentifier, pr_id: int, label_name: str):
        pass

    def merge(
        self,
        repository: RepositoryIdentifier,
        pr_id: int,
        commit_title: Optional[str],
        commit_message: Optional[str],
        method: MergeMethod,
        sha: str,
    ):
        pass

    def add_check(
        self,
        repository: RepositoryIdentifier,
        key: str,
        source_sha: str,
        details: CheckDetails,
    ):
        pass

    def update_check(
        self,
        repository: RepositoryIdentifier,
        key: str,
        source_sha: str,
        details: CheckDetails,
        remote_check_id: str,
    ):
        pass

    def update_pull_request(
        self,
        repository: RepositoryIdentifier,
        pr_id: int,
        sha: str,
    ):
        pass

    def get_pull_requests(self, repository: Repository) -> List[PullRequest]:
        pass

    def get_statuses(self, repository: RepositoryIdentifier, sha: str) -> List[Tuple[str, CheckStatus]]:
        pass

    def comment_on_pull_request(
        self,
        repository: RepositoryIdentifier,
        pr_id: int,
        sha: str,
        message: str,
    ):
        pass

    def get_pull_request_commits(
        self,
        repository: RepositoryIdentifier,
        pr_id: int,
    ) -> List[Commit]:
        pass

    def get_source_url(self, repository: RepositoryIdentifier, path: str) -> str:
        pass
