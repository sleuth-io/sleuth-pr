# Generated by Django 3.1.1 on 2020-09-26 07:32
from django.db import migrations
from django.db import models


class Migration(migrations.Migration):

    dependencies = [
        ("sleuthpr", "0004_pullrequestcheck"),
    ]

    operations = [
        migrations.AlterField(
            model_name="pullrequest",
            name="url",
            field=models.URLField(
                blank=True, max_length=1024, null=True, verbose_name="url"
            ),
        ),
    ]
