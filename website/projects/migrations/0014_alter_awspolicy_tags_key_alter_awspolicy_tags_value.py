# Generated by Django 4.1.3 on 2023-05-26 11:42

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("projects", "0013_remove_awspolicy_no_permissions_at_root_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="awspolicy",
            name="tags_key",
            field=models.CharField(blank=True, default="", max_length=50),
        ),
        migrations.AlterField(
            model_name="awspolicy",
            name="tags_value",
            field=models.CharField(blank=True, default="", max_length=50),
        ),
    ]
