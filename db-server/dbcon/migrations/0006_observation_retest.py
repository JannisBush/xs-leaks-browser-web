# Generated by Django 3.2.3 on 2021-06-09 15:06

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dbcon', '0005_observation_complete_time'),
    ]

    operations = [
        migrations.AddField(
            model_name='observation',
            name='retest',
            field=models.BooleanField(default=False),
        ),
    ]