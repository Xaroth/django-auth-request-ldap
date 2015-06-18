# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings
import django.utils.timezone


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Zone',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=128)),
                ('code', models.SlugField(max_length=128)),
                ('access', models.IntegerField(default=0, verbose_name='access', choices=[(0, 'Default'), (1, 'Allowed'), (2, 'Denied')])),
                ('enabled', models.BooleanField(default=True)),
            ],
            options={},
        ),
        migrations.CreateModel(
            name='ZoneGroup',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('access', models.IntegerField(default=0, verbose_name='access', choices=[(0, 'Default'), (1, 'Allowed'), (2, 'Denied')])),
                ('group', models.ForeignKey(related_name='+', to=settings.AUTH_GROUP_MODEL)),
                ('zone', models.ForeignKey(related_name='groups', to='auth_request.Zone')),
                ('order', models.IntegerField(default=10, verbose_name='order of importance')),
            ],
            options={
                'ordering': ['order'],
            },
        ),
        migrations.CreateModel(
            name='ZoneUser',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('access', models.IntegerField(default=0, verbose_name='access', choices=[(0, 'Default'), (1, 'Allowed'), (2, 'Denied')])),
                ('user', models.ForeignKey(related_name='+', to=settings.AUTH_USER_MODEL)),
                ('zone', models.ForeignKey(related_name='users', to='auth_request.Zone')),
                ('order', models.IntegerField(default=10, verbose_name='order of importance')),
            ],
            options={
                'ordering': ['order'],
            },
        ),
        migrations.CreateModel(
            name='LogEntry',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('timestamp', models.DateTimeField(default=django.utils.timezone.now)),
                ('username', models.CharField(max_length=90)),
                ('action', models.CharField(max_length=24, choices=[(b'access', 'Access'), (b'login', 'Logged In'), (b'logout', 'Logged Out'), (b'access_denied', 'Access Denied')])),
                ('message', models.CharField(max_length=127)),
                ('extra_data', models.CharField(max_length=127)),
                ('user', models.ForeignKey(related_name='+', to=settings.AUTH_USER_MODEL)),
                ('zone', models.ForeignKey(blank=True, to='auth_request.Zone', null=True)),
            ],
            options={
                'ordering': ['timestamp'],
            },
        ),
    ]
