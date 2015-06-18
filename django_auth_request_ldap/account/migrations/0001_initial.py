# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='User',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
            ],
            options={
                'verbose_name': 'user',
                'verbose_name_plural': 'users',
                'managed': False,
            }
        ),
        migrations.CreateModel(
            name='Group',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
            ],
            options={
                'verbose_name': 'group',
                'verbose_name_plural': 'groups',
                'managed': False,
            }
        ),
        migrations.CreateModel(
            name='SambaDomainName',
            fields=[
                ('domain_name', models.CharField(verbose_name='ID', max_length=200,
                                                 serialize=False, primary_key=True,
                                                 db_column=b'sambaDomainName')),
            ],
            options={
                'verbose_name': 'samba domain name',
                'verbose_name_plural': 'samba domain names',
                'managed': False,
            }
        ),
    ]
