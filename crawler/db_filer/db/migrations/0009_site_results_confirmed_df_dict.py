# Generated by Django 3.2.5 on 2021-08-31 10:33

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('db', '0008_site_results_confirmed_leak_urls'),
    ]

    operations = [
        migrations.AddField(
            model_name='site_results',
            name='confirmed_df_dict',
            field=models.JSONField(null=True),
        ),
    ]