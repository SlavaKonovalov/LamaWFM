# Generated by Django 3.1.4 on 2020-12-28 03:49

import datetime
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('wfm', '0011_auto_20201224_1224'),
    ]

    operations = [
        migrations.CreateModel(
            name='Scheduled_Production_Task',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('begin_date', models.DateField()),
                ('begin_time', models.TimeField(default=datetime.time(7, 0))),
                ('end_time', models.TimeField(default=datetime.time(18, 0))),
                ('work_scope', models.PositiveIntegerField(default=0)),
                ('repetition_type', models.CharField(choices=[('empty', 'Не задано'), ('day', 'День'), ('week', 'Неделя'), ('month', 'Месяц')], default='empty', max_length=20)),
                ('end_date', models.DateField(blank=True, null=True)),
                ('repetition_interval', models.PositiveIntegerField(blank=True, null=True)),
                ('exclude_holidays', models.BooleanField(default=False)),
                ('exclude_weekdays', models.BooleanField(default=False)),
                ('exclude_weekend', models.BooleanField(default=False)),
                ('day1_selection', models.BooleanField(default=False)),
                ('day2_selection', models.BooleanField(default=False)),
                ('day3_selection', models.BooleanField(default=False)),
                ('day4_selection', models.BooleanField(default=False)),
                ('day5_selection', models.BooleanField(default=False)),
                ('day6_selection', models.BooleanField(default=False)),
                ('day7_selection', models.BooleanField(default=False)),
                ('subdivision', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='scheduled_task_set', to='wfm.subdivision')),
                ('task', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='scheduled_task_set', to='wfm.production_task')),
            ],
        ),
    ]
