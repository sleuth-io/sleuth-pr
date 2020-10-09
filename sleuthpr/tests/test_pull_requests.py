import pytest

from sleuthpr.models import Repository
from sleuthpr.services import pull_requests
from sleuthpr.services.scm import Commit
from sleuthpr.tests.factories import RepositoryCommitFactory
from sleuthpr.tests.factories import RepositoryFactory


@pytest.mark.django_db
def test_sync_commits():
    repo: Repository = RepositoryFactory()
    changed = pull_requests.add_commits(
        repo,
        [
            Commit(
                sha="sha1",
                message="msg1",
                parents=["sha2"],
                author_name="Bob",
                author_email="bob@example.com",
                committer_name="Bob",
                committer_email="bob@example.com",
            )
        ],
    )
    assert len(changed) == 2
    assert repo.commits.all().count() == 3
    assert repo.commit_tree.filter(child__sha="sha1", parent__sha="sha2").count() == 1


@pytest.mark.django_db
def test_sync_commits_with_priors():
    repo: Repository = RepositoryFactory()
    RepositoryCommitFactory(repository=repo, sha="sha2", message="blah")
    changed = pull_requests.add_commits(
        repo,
        [
            Commit(
                sha="sha1",
                message="msg1",
                parents=["sha2"],
                author_name="Bob",
                author_email="bob@example.com",
                committer_name="Bob",
                committer_email="bob@example.com",
            )
        ],
    )
    assert len(changed) == 1
    assert repo.commits.all().count() == 3
    assert repo.commits.filter(sha="sha2").first().message == "blah"
    assert repo.commit_tree.filter(child__sha="sha1", parent__sha="sha2").count() == 1
