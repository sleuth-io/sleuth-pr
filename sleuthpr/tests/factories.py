import factory
from django.utils.text import slugify

from sleuthpr import models


class InstallationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.Installation

    remote_id = factory.Sequence(lambda n: f"remote_id_{n}")
    target_type = "organization"
    target_id = factory.Sequence(lambda n: f"org_{n}")
    provider = models.Provider.GITHUB


class RepositoryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.Repository

    installation = factory.SubFactory(InstallationFactory)
    full_name = factory.Sequence(lambda n: f"repo/repo-{n}")

    @factory.post_generation
    def branches(self, create, extracted, **kwargs):
        if not create:
            # Simple build, do nothing.
            return

        if not extracted:
            commit = RepositoryCommitFactory(repository=self)
            branches = [RepositoryBranchFactory(repository=self, head_sha=commit.sha)]
        else:
            branches = extracted

        for branch in branches:
            self.branches.add(branch)


class RepositoryBranchFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.RepositoryBranch

    repository = factory.SubFactory(RepositoryFactory)
    name = "master"
    head_sha = factory.Sequence(lambda n: f"head-{n}")

    @staticmethod
    def add_commit(repository: models.Repository, name: str, commit: models.RepositoryCommit):
        base_branch = repository.branches.filter(name=name).first()
        old_head = repository.commits.filter(sha=base_branch.head_sha).first()
        RepositoryCommitParentFactory(repository=repository, child=commit, parent=old_head)
        base_branch.head_sha = commit.sha
        base_branch.save()


class ExternalUserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.ExternalUser

    installation = factory.SubFactory(InstallationFactory)
    remote_id = factory.Sequence(lambda n: f"user-{n}")
    username = factory.Sequence(lambda n: f"username-{n}")


class RepositoryCommitFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.RepositoryCommit

    repository = factory.SubFactory(RepositoryFactory)
    sha = factory.Sequence(lambda n: f"sha-{n}")
    message = factory.Sequence(lambda n: f"Commit message {n}")
    pull_request = None
    committer = factory.SubFactory(ExternalUserFactory)
    author = factory.SubFactory(ExternalUserFactory)


class RepositoryCommitParentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.RepositoryCommitParent

    repository = factory.SubFactory(RepositoryFactory)
    child = factory.SubFactory(RepositoryCommitFactory)
    parent = factory.SubFactory(RepositoryCommitFactory)


class PullRequestFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.PullRequest

    repository: models.Repository = factory.SubFactory(RepositoryFactory)
    title = factory.Sequence(lambda n: f"My PR {n}")
    remote_id = factory.Sequence(lambda n: n)
    base_branch_name = "master"
    author = factory.SubFactory(ExternalUserFactory)

    @factory.post_generation
    def source_branch_name(self: models.PullRequest, create, extracted, **kwargs):
        if not create:
            return

        if not extracted:
            master = self.repository.branches.filter(name="master").first()
            master_head = self.repository.commits.filter(sha=master.head_sha).first()
            commit = RepositoryCommitFactory(repository=self.repository)
            branch = RepositoryBranchFactory(
                repository=self.repository, head_sha=commit.sha, name=f"branch/" f"{slugify(self.title)}"
            )
            RepositoryCommitParentFactory(repository=self.repository, parent=master_head, child=commit)
            commit.pull_request = self
            self.commits.set([commit])
        else:
            branch = extracted

        self.source_branch_name = branch.name


class PullRequestAssigneeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.PullRequestAssignee

    pull_request = factory.SubFactory(PullRequestFactory)
    user = factory.SubFactory(ExternalUserFactory)


class PullRequestReviewerFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.PullRequestReviewer

    pull_request = factory.SubFactory(PullRequestFactory)
    user = factory.SubFactory(ExternalUserFactory)


class PullRequestLabelFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.PullRequestLabel

    pull_request = factory.SubFactory(PullRequestFactory)
    value = factory.Sequence(lambda n: f"label-{n}")


class PullRequestStatusFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.PullRequestStatus

    pull_request = factory.SubFactory(PullRequestFactory)
    context = "foo"
    state = "success"
