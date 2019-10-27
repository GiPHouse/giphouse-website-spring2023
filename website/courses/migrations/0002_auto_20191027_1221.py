# Generated by Django 2.2.6 on 2019-10-27 11:21

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('courses', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='semester',
            name='registration_end',
            field=models.DateTimeField(blank=True, help_text='This must be filled in to open the registration.', null=True),
        ),
        migrations.AlterField(
            model_name='semester',
            name='registration_start',
            field=models.DateTimeField(blank=True, help_text='This must be filled in to open the registration.', null=True),
        ),
    ]
