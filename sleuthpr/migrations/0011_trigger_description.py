# Generated by Django 3.1.1 on 2020-10-09 05:30
from django.db import migrations
from django.db import models


class Migration(migrations.Migration):

    dependencies = [
        ("sleuthpr", "0010_delete_conditioncheckrun"),
    ]

    operations = [
        migrations.AddField(
            model_name="trigger",
            name="description",
            field=models.TextField(blank=True, default="", max_length=16384, verbose_name="description"),
        ),
    ]
