# Generated by Django 3.2.9 on 2022-10-27 08:45

from django.db import migrations, models
import django.db.models.deletion
import utils.shortcuts


class Migration(migrations.Migration):

    dependencies = [
        ('quiz', '0001_initial'),
        ('contest', '0011_auto_20221027_1745'),
        ('submission', '0012_auto_20180501_0436'),
    ]

    operations = [
        migrations.AlterField(
            model_name='submission',
            name='info',
            field=models.JSONField(default=dict),
        ),
        migrations.AlterField(
            model_name='submission',
            name='statistic_info',
            field=models.JSONField(default=dict),
        ),
        migrations.CreateModel(
            name='QuizSubmission',
            fields=[
                ('id', models.TextField(db_index=True, default=utils.shortcuts.rand_str, primary_key=True, serialize=False)),
                ('create_time', models.DateTimeField(auto_now_add=True)),
                ('user_id', models.IntegerField(db_index=True)),
                ('username', models.TextField()),
                ('submit', models.TextField()),
                ('result', models.IntegerField(db_index=True, default=6)),
                ('info', models.JSONField(default=dict)),
                ('shared', models.BooleanField(default=False)),
                ('ip', models.TextField(null=True)),
                ('contest', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='contest.contest')),
                ('quiz', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='quiz.quiz')),
            ],
            options={
                'db_table': 'QuizSubmission',
                'ordering': ('-create_time',),
            },
        ),
    ]