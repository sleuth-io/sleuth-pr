import logging

from sleuthpr.models import Installation
from sleuthpr.models import Repository
from sleuthpr.models import RepositoryBranch
from sleuthpr.services import pull_requests
from sleuthpr.util import dirty_set_all

logger = logging.getLogger(__name__)


def update_sha(installation: Installation, repository: Repository, name: str, sha: str):
    existing = repository.branches.filter(name=name).first()
    if not existing:
        RepositoryBranch.objects.create(repository=repository, name=name, head_sha=sha)
        dirty = True
    else:
        dirty = dirty_set_all(existing, dict(head_sha=sha))

    if dirty:
        pull_requests.on_source_change(installation, repository, name, sha)
