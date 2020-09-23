import logging
from typing import List

from sleuthpr.models import Installation
from sleuthpr.models import Repository
from sleuthpr.models import RepositoryIdentifier
from sleuthpr.services import rules

logger = logging.getLogger(__name__)


def add(installation: Installation, repository_ids: List[RepositoryIdentifier]):
    if not repository_ids:
        raise ValueError("No repository_ids available for this installation")

    for repo in repository_ids:
        repository = Repository.objects.create(
            installation=installation, full_name=repo.full_name
        )

        contents = installation.client.get_content(
            repository.identifier, ".sleuth/rules.yml"
        )
        if contents:
            rules.refresh(repository, contents)
        logger.info(f"Registered repo {repo.full_name}")


def remove(installation: Installation, repository_ids: List[RepositoryIdentifier]):
    if not repository_ids:
        raise ValueError("No repository_ids available to remove")

    Repository.objects.filter(
        installation=installation, full_name__in=repository_ids
    ).delete()
    logger.info(f"Deleted repos {repository_ids}")


def set_repositories(
    installation: Installation, repository_ids: List[RepositoryIdentifier]
):
    Repository.objects.filter(installation=installation).delete()
    return add(installation, repository_ids)
