# Generated by Django 4.1.3 on 2023-02-15 20:50

from django.db import migrations
import tinymce.models


class Migration(migrations.Migration):

    dependencies = [
        ("projects", "0006_alter_project_unique_together_project_slug_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="project",
            name="description",
            field=tinymce.models.HTMLField(),
        ),
    ]
