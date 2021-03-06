from os import access, X_OK
from django.conf import settings
from django.contrib import auth
from django.db import DEFAULT_DB_ALIAS

import ldapdb
from ldapdb.router import Router as LDAPDBRouter, is_ldap_model

LDAP_DN_SUFFIX = getattr(settings, 'LDAP_DN_SUFFIX', '')
ALLOWED_LDAP_RELATIONS = getattr(settings, 'ALLOWED_LDAP_RELATIONS', [])


class Router(LDAPDBRouter):
    def allow_relation(self, obj, to):
        obj_name = '%s.%s' % (obj._meta.app_label, obj._meta.object_name)
        to_name = '%s.%s' % (to._meta.app_label, to._meta.object_name)
        return obj._meta.app_label == to._meta.app_label or \
            obj._state.db == to._state.db or \
            (obj_name, to_name) in ALLOWED_LDAP_RELATIONS

    def db_for_write(self, model, **hints):
        "Point all operations on LDAP models to the LDAP database"
        if is_ldap_model(model):
            return self.ldap_alias
        instance = hints.get('instance')
        if instance is not None and instance._state.db:
            if instance._state.db == self.ldap_alias:  # this prevents issues when relating over databases.
                return DEFAULT_DB_ALIAS
        return None


def process_shells(items):
    return [(x, x.rsplit('/')[-1]) for x in items if access(x, X_OK)]


class classproperty(object):
    def __init__(self, getter):
        self.getter = getter

    def __get__(self, instance, owner):
        return self.getter(owner)


class CustomRDNModel(ldapdb.models.Model):
    dn_prefix = None
    dn_suffix = None

    @classproperty
    def base_dn(cls):
        suf = cls.dn_suffix or LDAP_DN_SUFFIX
        parts = [cls.dn_prefix, suf]
        return ','.join([x for x in parts if x])

    class Meta:
        abstract = True


class PermissionsIterator(object):
    def get_all_permissions(self):
        from django.contrib.auth.models import Permission
        items = []
        try:
            for perm in Permission.objects.all().select_related('content_type'):
                app_label = perm.content_type.app_label
                items.append(('%s.%s' % (app_label, perm.codename), '%s | %s' % (app_label, perm.name)))
        except:
            pass
        return items

    def __init__(self):
        self.cached = None

    def load(self):
        if not self.cached:
            self.cached = self.get_all_permissions()
        return self.cached

    def __iter__(self):
        return iter(self.load())

    def __getitem__(self, index):
        return self.load()[index]


# A few helper functions for common logic between User and AnonymousUser.
def _user_get_all_permissions(user, obj):
    permissions = set()
    for backend in auth.get_backends():
        if hasattr(backend, "get_all_permissions"):
            permissions.update(backend.get_all_permissions(user, obj))
    return permissions


def _user_has_perm(user, perm, obj):
    for backend in auth.get_backends():
        if hasattr(backend, "has_perm"):
            if backend.has_perm(user, perm, obj):
                return True
    return False


def _user_has_module_perms(user, app_label):
    for backend in auth.get_backends():
        if hasattr(backend, "has_module_perms"):
            if backend.has_module_perms(user, app_label):
                return True
    return False
