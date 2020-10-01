import factory

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


class RepositoryBranchFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.RepositoryBranch

    repository = factory.SubFactory(RepositoryFactory)
    name = "master"
    head_sha = factory.Sequence(lambda n: f"head-{n}")


class RepositoryCommitFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.RepositoryCommit

    repository = factory.SubFactory(RepositoryFactory)
    sha = factory.Sequence(lambda n: f"sha-{n}")
    message = factory.Sequence(lambda n: f"Commit message {n}")
    pull_request = None


class RepositoryCommitParentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.RepositoryCommitParent

    repository = factory.SubFactory(RepositoryFactory)
    child = factory.SubFactory(RepositoryCommitFactory)
    parent = factory.SubFactory(RepositoryCommitFactory)


class ExternalUserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.ExternalUser

    installation = factory.SubFactory(InstallationFactory)
    remote_id = factory.Sequence(lambda n: f"user-{n}")
    username = factory.Sequence(lambda n: f"username-{n}")


class PullRequestFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.PullRequest

    repository = factory.SubFactory(RepositoryFactory)
    title = factory.Sequence(lambda n: f"My PR {n}")
    remote_id = factory.Sequence(lambda n: n)
    source_branch_name = factory.Sequence(lambda n: f"mybranch-{n}")
    base_branch_name = "master"
    author = factory.SubFactory(ExternalUserFactory)


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
