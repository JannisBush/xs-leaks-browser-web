# Generated by Django 3.2.3 on 2021-06-09 09:02

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dbcon', '0004_auto_20210604_2026'),
    ]

    operations = [
        migrations.AddField(
            model_name='observation',
            name='complete_time',
            field=models.IntegerField(null=True),
        ),
    ]