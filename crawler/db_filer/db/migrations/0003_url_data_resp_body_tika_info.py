# Generated by Django 3.2.5 on 2021-07-19 12:19

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('db', '0002_url_data_real_site'),
    ]

    operations = [
        migrations.AddField(
            model_name='url_data',
            name='resp_body_tika_info',
            field=models.TextField(default='a'),
            preserve_default=False,
        ),
    ]