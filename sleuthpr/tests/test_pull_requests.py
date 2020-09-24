import json
from os.path import dirname
from os.path import join

import pytest

from sleuthpr.services import pull_requests
from sleuthpr.tests.factories import RepositoryFactory


@pytest.mark.django_db
def test_basic():
    repository = RepositoryFactory()
    with open(join(dirname(__file__), "pr.json")) as f:
        data = json.load(f)
    pr = pull_requests.update(repository.installation, repository, data)
    assert 1347 == pr.remote_id

    assert 2 == len(pr.assignees.all())
    assert 1 == len(pr.reviewers.all())
    assert 1 == len(pr.labels.all())
    assert "bug" == pr.labels.first().value
