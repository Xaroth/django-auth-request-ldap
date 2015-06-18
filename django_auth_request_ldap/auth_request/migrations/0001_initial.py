# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        migrations.swappable_dependency(settings.AUTH_GROUP_MODEL),
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
        ),
        migrations.CreateModel(
            name='ZoneGroup',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('access', models.IntegerField(default=0, verbose_name='access', choices=[(0, 'Default'), (1, 'Allowed'), (2, 'Denied')])),
                ('group', models.ForeignKey(to=settings.AUTH_GROUP_MODEL)),
                ('zone', models.ForeignKey(to='auth_request.Zone')),
            ],
        ),
        migrations.CreateModel(
            name='ZoneUser',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('access', models.IntegerField(default=0, verbose_name='access', choices=[(0, 'Default'), (1, 'Allowed'), (2, 'Denied')])),
                ('user', models.ForeignKey(to=settings.AUTH_USER_MODEL)),
                ('zone', models.ForeignKey(to='auth_request.Zone')),
            ],
        ),
    ]
