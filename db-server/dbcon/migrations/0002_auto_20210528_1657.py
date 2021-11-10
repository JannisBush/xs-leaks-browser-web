# Generated by Django 3.2.3 on 2021-05-28 16:57

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('dbcon', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Browser',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('browser', models.TextField()),
                ('version', models.TextField()),
                ('headless', models.BooleanField(default=False)),
            ],
        ),
        migrations.CreateModel(
            name='Events',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('event_set', models.TextField(default='nA')),
                ('event_list', models.TextField(default='nA')),
            ],
        ),
        migrations.CreateModel(
            name='GlobalProperties',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('gp_window_onerror', models.TextField(default='nA')),
                ('gp_window_onblur', models.TextField(default='nA')),
                ('gp_window_postMessage', models.TextField(default='nA')),
                ('gp_window_getComputedStyle', models.TextField(default='nA')),
                ('gp_window_hasOwnProperty', models.TextField(default='nA')),
                ('gp_download_bar_height', models.TextField(default='nA')),
                ('gp_securitypolicyviolation', models.TextField(default='nA')),
            ],
        ),
        migrations.CreateModel(
            name='ObjectProperties',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('op_frame_count', models.TextField(default='nA')),
                ('op_win_window', models.TextField(default='nA')),
                ('op_win_CSS2Properties', models.TextField(default='nA')),
                ('op_win_origin', models.TextField(default='nA')),
                ('op_win_opener', models.TextField(default='nA')),
                ('op_el_height', models.TextField(default='nA')),
                ('op_el_width', models.TextField(default='nA')),
                ('op_el_naturalHeight', models.TextField(default='nA')),
                ('op_el_naturalWidth', models.TextField(default='nA')),
                ('op_el_videoWidth', models.TextField(default='nA')),
                ('op_el_videoHeight', models.TextField(default='nA')),
                ('op_el_duration', models.TextField(default='nA')),
                ('op_el_networkState', models.TextField(default='nA')),
                ('op_el_readyState', models.TextField(default='nA')),
                ('op_el_buffered', models.TextField(default='nA')),
                ('op_el_paused', models.TextField(default='nA')),
                ('op_el_seekable', models.TextField(default='nA')),
                ('op_el_sheet', models.TextField(default='nA')),
                ('op_el_media_error', models.TextField(default='nA')),
            ],
        ),
        migrations.CreateModel(
            name='Observation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('loading_time', models.IntegerField(null=True)),
                ('timed_out', models.BooleanField(default=False)),
                ('apg_url', models.TextField(null=True)),
            ],
        ),
        migrations.CreateModel(
            name='Test',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('test_url', models.TextField()),
                ('inc_method', models.TextField()),
                ('url_dict_version', models.TextField()),
            ],
        ),
        migrations.AddConstraint(
            model_name='test',
            constraint=models.UniqueConstraint(fields=('test_url', 'inc_method', 'url_dict_version'), name='test'),
        ),
        migrations.AddField(
            model_name='observation',
            name='browser',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='dbcon.browser'),
        ),
        migrations.AddField(
            model_name='observation',
            name='events',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='dbcon.events'),
        ),
        migrations.AddField(
            model_name='observation',
            name='global_properties',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='dbcon.globalproperties'),
        ),
        migrations.AddField(
            model_name='observation',
            name='object_properties',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='dbcon.objectproperties'),
        ),
        migrations.AddField(
            model_name='observation',
            name='test',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='dbcon.test'),
        ),
        migrations.AddConstraint(
            model_name='objectproperties',
            constraint=models.UniqueConstraint(fields=('op_frame_count', 'op_win_window', 'op_win_CSS2Properties', 'op_win_origin', 'op_win_opener', 'op_el_height', 'op_el_width', 'op_el_naturalHeight', 'op_el_naturalWidth', 'op_el_videoHeight', 'op_el_videoWidth', 'op_el_duration', 'op_el_networkState', 'op_el_readyState', 'op_el_buffered', 'op_el_paused', 'op_el_seekable', 'op_el_sheet', 'op_el_media_error'), name='op'),
        ),
        migrations.AddConstraint(
            model_name='globalproperties',
            constraint=models.UniqueConstraint(fields=('gp_window_onerror', 'gp_window_onblur', 'gp_window_postMessage', 'gp_window_getComputedStyle', 'gp_window_hasOwnProperty', 'gp_download_bar_height', 'gp_securitypolicyviolation'), name='gp'),
        ),
        migrations.AddConstraint(
            model_name='events',
            constraint=models.UniqueConstraint(fields=('event_set', 'event_list'), name='events'),
        ),
        migrations.AddConstraint(
            model_name='browser',
            constraint=models.UniqueConstraint(fields=('browser', 'version', 'headless'), name='browser'),
        ),
    ]