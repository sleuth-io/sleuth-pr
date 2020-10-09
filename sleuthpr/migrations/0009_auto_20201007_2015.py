# Generated by Django 3.1.1 on 2020-10-07 20:15
import django.db.models.deletion
from django.db import migrations
from django.db import models


class Migration(migrations.Migration):

    dependencies = [
        ("sleuthpr", "0008_auto_20201001_2012"),
    ]

    operations = [
        migrations.AlterField(
            model_name="conditioncheckrun",
            name="condition",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="checks_old",
                to="sleuthpr.condition",
                verbose_name="condition",
            ),
        ),
        migrations.AlterField(
            model_name="conditioncheckrun",
            name="pull_request",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="checks_old",
                to="sleuthpr.pullrequest",
                verbose_name="pull_request",
            ),
        ),
        migrations.CreateModel(
            name="RuleCheckRun",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("success", "Success"),
                            ("failure", "Failure"),
                            ("pending", "Pending"),
                            ("error", "Error"),
                        ],
                        db_index=True,
                        max_length=50,
                    ),
                ),
                ("remote_id", models.CharField(db_index=True, max_length=512)),
                (
                    "pull_request",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="checks",
                        to="sleuthpr.pullrequest",
                        verbose_name="pull_request",
                    ),
                ),
                (
                    "rule",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="checks",
                        to="sleuthpr.rule",
                        verbose_name="rule",
                    ),
                ),
            ],
        ),
    ]