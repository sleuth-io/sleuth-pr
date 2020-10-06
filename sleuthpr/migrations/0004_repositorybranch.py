# Generated by Django 3.1.1 on 2020-09-30 20:43
import django.db.models.deletion
from django.db import migrations
from django.db import models


class Migration(migrations.Migration):

    dependencies = [
        ("sleuthpr", "0003_auto_20200930_2010"),
    ]

    operations = [
        migrations.CreateModel(
            name="RepositoryBranch",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(db_index=True, max_length=255, verbose_name="name")),
                ("head_sha", models.CharField(db_index=True, max_length=1024, verbose_name="head sha")),
                (
                    "repository",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="branches",
                        to="sleuthpr.repository",
                        verbose_name="repository",
                    ),
                ),
            ],
        ),
    ]