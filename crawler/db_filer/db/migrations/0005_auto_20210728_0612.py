# Generated by Django 3.2.5 on 2021-07-28 06:12

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('db', '0004_auto_20210720_0519'),
    ]

    operations = [
        migrations.CreateModel(
            name='site_results',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('site', models.TextField(unique=True)),
                ('login', models.TextField()),
                ('cookies', models.JSONField(null=True)),
                ('cookie_end', models.TextField()),
                ('num_urls', models.IntegerField(null=True)),
                ('num_basic_pruning', models.IntegerField(null=True)),
                ('num_input_rows', models.IntegerField(null=True)),
                ('crawl_end', models.TextField()),
                ('dyn_conf_urls', models.JSONField(null=True)),
                ('dyn_conf_firefox', models.IntegerField(null=True)),
                ('dyn_conf_chrome', models.IntegerField(null=True)),
                ('dyn_end', models.TextField()),
                ('dyn_conf_retest_urls', models.JSONField(null=True)),
                ('dyn_conf_retest_firefox', models.IntegerField(null=True)),
                ('dyn_conf_retest_chrome', models.IntegerField(null=True)),
                ('dyn_retest_end', models.TextField()),
                ('confirmed_urls', models.JSONField(null=True)),
                ('confirmed_urls_firefox', models.IntegerField(null=True)),
                ('confirmed_urls_chrome', models.IntegerField(null=True)),
            ],
        ),
        migrations.AddIndex(
            model_name='site_results',
            index=models.Index(fields=['site'], name='db_site_res_site_a3e991_idx'),
        ),
    ]