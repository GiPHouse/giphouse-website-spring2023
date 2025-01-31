# Generated by Django 4.1.3 on 2023-05-26 09:31

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("projects", "0010_alter_awspolicy_is_current_policy_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="awspolicy",
            name="is_current_policy",
            field=models.BooleanField(
                default=False,
                help_text="Attention: When saving this policy, all other policies will be set to 'not current'!",
            ),
        ),
    ]
