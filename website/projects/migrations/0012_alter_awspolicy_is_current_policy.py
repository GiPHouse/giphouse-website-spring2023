# Generated by Django 4.1.3 on 2023-05-26 09:32

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("projects", "0011_alter_awspolicy_is_current_policy"),
    ]

    operations = [
        migrations.AlterField(
            model_name="awspolicy",
            name="is_current_policy",
            field=models.BooleanField(
                default=False,
                help_text="Attention: When saving this policy with 'is current policy' checked, all other policies will be set to 'not current'!",
            ),
        ),
    ]
