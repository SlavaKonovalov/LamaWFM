# Generated by Django 3.1.4 on 2020-12-23 11:00

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('wfm', '0008_auto_20201223_1508'),
    ]

    operations = [
        migrations.AlterField(
            model_name='production_task',
            name='demand_allocation_method',
            field=models.CharField(choices=[('soft', 'Свободное'), ('continuous', 'Непрерывное'), ('hard', 'Равномерное')], default='soft', max_length=20),
        ),
        migrations.AddField(
            model_name='production_task',
            name='organization',
            field=models.ForeignKey(default='1',on_delete=django.db.models.deletion.CASCADE, to='wfm.organization'),
			preserve_default=True,
        ),
		migrations.AlterField(
            model_name='production_task',
            name='work_scope_measure',
            field=models.CharField(choices=[('minutes', 'Минуты'), ('pieces', 'Штуки')], default='minutes', max_length=20),
        ),
    ]
