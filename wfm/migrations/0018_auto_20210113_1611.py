# Generated by Django 3.1.4 on 2021-01-13 09:11

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('wfm', '0017_auto_20210113_1610'),
    ]

    operations = [
        migrations.AlterField(
            model_name='employee',
            name='duties',
            field=models.ManyToManyField(blank=True, null=True, to='wfm.Job_Duty'),
        ),
        migrations.AlterField(
            model_name='employee',
            name='part_time_job_org',
            field=models.ManyToManyField(blank=True, null=True, to='wfm.Organization'),
        ),
    ]
