import logging
from typing import List
from typing import Optional

from sleuthpr.models import Installation
from sleuthpr.models import RepositoryIdentifier
from sleuthpr.services import repositories

logger = logging.getLogger(__name__)


def get(remote_id: str) -> Optional[Installation]:
    return Installation.objects.filter(remote_id=remote_id).filter(active=True).first()


def delete(installation: Installation) -> bool:
    installation.delete()
    logger.info("Deleted installation")
    return True


def suspend(installation: Installation) -> bool:
    if installation and installation.active:
        installation.active = False
        installation.save()
        logger.info("Suspended installation")
        return True
    else:
        return False


def unsuspend(installation: Installation) -> bool:
    if installation and not installation.active:
        installation.active = True
        installation.save()
        logger.info("Unsuspended installation")
        return True
    else:
        return False


def create(
    remote_id: str,
    target_type: str,
    target_id: str,
    repository_ids: List[RepositoryIdentifier],
    provider: str,
) -> Installation:
    installation = Installation.objects.create(
        remote_id=remote_id,
        target_type=target_type,
        target_id=target_id,
        provider=provider,
    )

    if not repository_ids:
        repository_ids = installation.client.get_repositories()

    repositories.add(installation, repository_ids)

    logger.info(f"Created installation {remote_id}")

    return installation
