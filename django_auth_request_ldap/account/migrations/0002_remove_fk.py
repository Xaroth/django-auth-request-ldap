# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings

ACCOUNT_MIGRATION_APPS = getattr(settings, "ACCOUNT_MIGRATION_APPS", [("account", "LogEntry", "user")])


class SpecialAlterField(migrations.AlterField):
    def __init__(self, app_label, *args, **kwargs):
        self.app_label = app_label
        super(SpecialAlterField, self).__init__(*args, **kwargs)

    def state_forwards(self, app_label, state):
        super(SpecialAlterField, self).state_forwards(self.app_label, state)

    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        super(SpecialAlterField, self).database_forwards(self.app_label, schema_editor, from_state, to_state)

    def database_backwards(self, app_label, schema_editor, from_state, to_state):
        super(SpecialAlterField, self).database_backwards(self.app_label, schema_editor, from_state, to_state)

    def deconstruct(self):
        kwargs = {
            'app_label': self.app_label,
            'model_name': self.model_name,
            'name': self.name,
            'field': self.field,
        }
        if self.preserve_default is not True:
            kwargs['preserve_default'] = self.preserve_default
        return (
            self.__class__.__name__,
            [],
            kwargs
        )


class SpecialRenameField(migrations.RenameField):
    def __init__(self, app_label, *args, **kwargs):
        self.app_label = app_label
        super(SpecialRenameField, self).__init__(*args, **kwargs)

    def state_forwards(self, app_label, state):
        super(SpecialRenameField, self).state_forwards(self.app_label, state)

    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        super(SpecialRenameField, self).database_forwards(self.app_label, schema_editor, from_state, to_state)

    def database_backwards(self, app_label, schema_editor, from_state, to_state):
        super(SpecialRenameField, self).database_backwards(self.app_label, schema_editor, from_state, to_state)

    def deconstruct(self):
        kwargs = {
            'app_label': self.app_label,
            'model_name': self.model_name,
            'old_name': self.old_name,
            'new_name': self.new_name,
        }
        return (
            self.__class__.__name__,
            [],
            kwargs
        )


def build_ops():
    for app_label, model_name, field_name in ACCOUNT_MIGRATION_APPS:
        yield SpecialRenameField(
            app_label=app_label,
            model_name=model_name,
            old_name=field_name,
            new_name="%s_id" % field_name)
        yield SpecialAlterField(
            app_label=app_label,
            model_name=model_name,
            name="%s_id" % field_name,
            field=models.IntegerField())
operations = list(build_ops())
dependencies = [(app_label, '0001_initial') for app_label, model_name, field_name in ACCOUNT_MIGRATION_APPS]


class Migration(migrations.Migration):
    dependencies = dependencies
    operations = operations
