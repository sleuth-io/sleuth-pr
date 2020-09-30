import json
from os.path import dirname
from os.path import join

import pytest

from sleuthpr.models import TriState
from sleuthpr.services.github.events import _update_pull_request
from sleuthpr.tests.factories import RepositoryFactory


@pytest.mark.django_db
def test_update_pull_request():
    repository = RepositoryFactory()
    with open(join(dirname(__file__), "pr.json")) as f:
        data = json.load(f)
    pr, dirty = _update_pull_request(repository.installation, repository, data)

    assert dirty
    assert "1347" == pr.remote_id

    assert 2 == len(pr.assignees.all())
    assert 1 == len(pr.reviewers.all())
    assert 1 == len(pr.labels.all())
    assert "bug" == pr.labels.first().value
    assert "6dcb09b5b57875f334f61aebed695e2e4193db5e" == pr.source_sha
    assert not pr.merged
    assert not pr.draft
    assert pr.mergeable == TriState.TRUE
    assert pr.rebaseable

    pr, dirty = _update_pull_request(repository.installation, repository, data)

    assert not dirty
