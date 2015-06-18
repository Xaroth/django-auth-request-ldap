# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings

ACCOUNT_MIGRATION_APPS = getattr(settings, "ACCOUNT_MIGRATION_APPS", [("admin", "LogEntry", "user", "__first__")])


class RemoteModel(object):
    def __init__(self, app_label, *args, **kwargs):
        self.app_label = app_label
        super(RemoteModel, self).__init__(*args, **kwargs)

    def state_forwards(self, app_label, state):
        super(RemoteModel, self).state_forwards(self.app_label, state)

    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        super(RemoteModel, self).database_forwards(self.app_label, schema_editor, from_state, to_state)

    def database_backwards(self, app_label, schema_editor, from_state, to_state):
        super(RemoteModel, self).database_backwards(self.app_label, schema_editor, from_state, to_state)

    def deconstruct(self):
        name, args, kwargs = super(RemoteModel, self).deconstruct()
        kwargs['app_label'] = self.app_label
        return (name, args, kwargs)


class SpecialAlterField(RemoteModel, migrations.AlterField):
    pass


class SpecialRenameField(RemoteModel, migrations.RenameField):
    pass


class SpecialAlterModelOptions(RemoteModel, migrations.AlterModelOptions):
    pass


def build_ops():
    for app_label, model_name, field_name, dep_name in ACCOUNT_MIGRATION_APPS:
        yield SpecialRenameField(
            app_label=app_label,
            model_name=model_name,
            old_name=field_name,
            new_name="%s_id" % field_name)
        yield SpecialAlterField(
            app_label=app_label,
            model_name=model_name,
            name="%s_id" % field_name,
            field=models.IntegerField(null=False, default=-1))
        yield SpecialAlterModelOptions(
            app_label=app_label,
            name=model_name,
            options={'managed': 'False'})
operations = list(build_ops())
dependencies = [(app_label, dep_name) for app_label, model_name, field_name, dep_name in ACCOUNT_MIGRATION_APPS if dep_name]


class Migration(migrations.Migration):
    dependencies = [('account', '0001_initial')] + dependencies
    operations = operations
