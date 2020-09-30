import logging
from typing import List
from typing import Optional

from django.db.models import QuerySet

from sleuthpr.models import Installation
from sleuthpr.models import Repository
from sleuthpr.models import RepositoryIdentifier
from sleuthpr.services import pull_requests
from sleuthpr.services import rules

logger = logging.getLogger(__name__)


def add(installation: Installation, repository_ids: List[RepositoryIdentifier]):
    if not repository_ids:
        raise ValueError("No repository_ids available for this installation")

    for repo in repository_ids:
        repository = Repository.objects.create(
            installation=installation,
            full_name=repo.full_name,
            remote_id=repo.remote_id,
        )

        rules.refresh(installation, repository)
        pull_requests.refresh(installation, repository)
        logger.info(f"Registered repo {repo.full_name}")


def remove(installation: Installation, repository_ids: List[RepositoryIdentifier]):
    if not repository_ids:
        raise ValueError("No repository_ids available to remove")

    Repository.objects.filter(installation=installation, full_name__in=repository_ids).delete()
    logger.info(f"Deleted repos {repository_ids}")


def set_repositories(installation: Installation, repository_ids: List[RepositoryIdentifier]):
    Repository.objects.filter(installation=installation).delete()
    return add(installation, repository_ids)


def get_all(repository_id: RepositoryIdentifier) -> QuerySet[Repository]:
    return (
        Repository.objects.filter(full_name=repository_id.full_name, installation__active=True)
        .select_related("installation")
        .all()
    )


def get(installation: Installation, repository_id: RepositoryIdentifier) -> Optional[Repository]:
    return Repository.objects.filter(
        full_name=repository_id.full_name,
        installation__active=True,
        installation=installation,
    ).first()
