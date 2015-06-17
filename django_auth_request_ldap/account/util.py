from os import access, X_OK
from django.conf import settings
from django.contrib import auth

import ldapdb

LDAP_DN_SUFFIX = getattr(settings, 'LDAP_DN_SUFFIX', '')


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
