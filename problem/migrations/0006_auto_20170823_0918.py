# -*- coding: utf-8 -*-
# Generated by Django 1.9.6 on 2017-08-23 09:18
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('problem', '0005_auto_20170815_1258'),
    ]

    operations = [
        migrations.RenameField(
            model_name='contestproblem',
            old_name='total_accepted_number',
            new_name='accepted_number',
        ),
        migrations.RenameField(
            model_name='contestproblem',
            old_name='total_submit_number',
            new_name='submission_number',
        ),
        migrations.RenameField(
            model_name='problem',
            old_name='total_accepted_number',
            new_name='accepted_number',
        ),
        migrations.RenameField(
            model_name='problem',
            old_name='total_submit_number',
            new_name='submission_number',
        ),
    ]
