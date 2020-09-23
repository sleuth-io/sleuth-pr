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
