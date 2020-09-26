from __future__ import annotations

import typing
from dataclasses import dataclass
from typing import Any
from typing import Dict
from typing import List
from typing import Optional

if typing.TYPE_CHECKING:
    from sleuthpr.models import (
        Installation,
        RepositoryIdentifier,
        PullRequest,
        MergeMethod,
    )


@dataclass
class CheckDetails:
    title: str
    summary: str
    body: str
    success: bool


def get_client(installation: Installation):
    if installation.provider == "github":
        from sleuthpr.services.github import GitHubInstallationClient

        return GitHubInstallationClient(installation)
    else:
        raise ValueError(f"Unsupported provider: {installation.provider}")
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
