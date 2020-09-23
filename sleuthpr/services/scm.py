from __future__ import annotations

import typing
from typing import Any
from typing import Dict
from typing import List
from typing import Optional

if typing.TYPE_CHECKING:
    from sleuthpr.models import Installation, RepositoryIdentifier


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
