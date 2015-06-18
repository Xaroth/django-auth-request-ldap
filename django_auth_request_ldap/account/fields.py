from django import forms
from django.conf import settings
from django.db import models, router
from django.db.models import fields, SubfieldBase
try:
    from django.db.models.related import PathInfo
except ImportError:
    from django.db.models.query_utils import PathInfo
from django.db.models.query import QuerySet
from django.db.models.fields.related import ManyToOneRel, RelatedField
from django.db.models.query_utils import DeferredAttribute
from django.utils import timezone, six
from django.utils.functional import cached_property
from ldapdb import escape_ldap_filter
from ldapdb.models.fields import ListField, IntegerField as LDAPIntegerField

import calendar
import datetime

from .utils import LDAP_DN_SUFFIX

LDAP_LIST_DEFAULT = getattr(settings, 'LDAP_LIST_DEFAULT', None) or ('cn=admin,%s' % LDAP_DN_SUFFIX)


class DateTimeField(fields.DateTimeField):
    def from_ldap(self, value, connection):
        if len(value) == 0:
            value = 0
        else:
            value = int(value[0])
        return timezone.make_aware(datetime.datetime.utcfromtimestamp(value), timezone.utc)

    def to_ldap(self, value, connection=None):
        if isinstance(value, six.string_types):
            return value
        if not timezone.is_aware(value):
            value = timezone.make_aware(value, timezone.utc)
        return str(calendar.timegm(value.utctimetuple()))

    def get_db_prep_save(self, value, connection):
        if not value:
            return None
        return [self.to_ldap(value, connection)]

    def get_prep_lookup(self, lookup_type, value):
        if lookup_type in ('exact', 'gte', 'lte'):
            return self.to_ldap(value)
        raise TypeError("IntegerField has invalid lookup: %s" % lookup_type)

    def formfield(self, **kwargs):
        defaults = {'form_class': forms.DateTimeField}
        defaults.update(kwargs)
        return super(DateTimeField, self).formfield(**defaults)


class BooleanField(fields.BooleanField):
    def from_ldap(self, value, connection):
        if len(value) == 0:
            return False
        else:
            return True if value[0].lower() == 'true' else False

    def get_db_prep_lookup(self, lookup_type, value, connection, prepared=False):
        "Returns field's value prepared for database lookup."
        return [self.get_prep_lookup(lookup_type, value)]

    def get_db_prep_save(self, value, connection):
        return [str(value).upper()]

    def get_prep_lookup(self, lookup_type, value):
        "Perform preliminary non-db specific lookup checks and conversions"
        if lookup_type == 'exact':
            if not isinstance(value, bool):
                if (not value) or (isinstance(value, six.string_types) and value.lower() in("false", "0")):
                    return escape_ldap_filter("FALSE")
                return escape_ldap_filter("TRUE")
            return escape_ldap_filter(value)
        raise TypeError("BooleanField has invalid lookup: %s" % lookup_type)

    def to_python(self, value):
        if not value:
            return False
        return value


class DefaultListField(ListField):
    __metaclass__ = SubfieldBase

    def __init__(self, default=LDAP_LIST_DEFAULT, *args, **kwargs):
        super(ListField, self).__init__(*args, **kwargs)
        self.default = default

    def pre_save(self, model_instance, add):
        val = getattr(model_instance, self.attname)
        return val

    def get_db_prep_save(self, value, connection):
        if len(value) == 0:
            value = [self.default]
        return super(DefaultListField, self).get_db_prep_save(value, connection)

    def get_db_prep_value(self, value, connection, prepared=False):
        return super(DefaultListField, self).get_db_prep_value(value, connection, prepared)

    def to_python(self, value):
        value = super(DefaultListField, self).to_python(value)
        if value == self.default:
            return []
        if self.default in value:
            value.remove(self.default)
        return value

    def formfield(self, **kwargs):
        defaults = {'form_class': forms.MultipleChoiceField}
        defaults.update(kwargs)
        return super(DefaultListField, self).formfield(**defaults)


def create_related_manager(from_model, from_field_name, to_model, to_field_name):  # noqa
    class RelatedManager(models.Manager):
        def __init__(self, instance):
            super(RelatedManager, self).__init__()
            self.instance = instance
            self.model = to_model

        def __call__(self, **kwargs):
            manager = create_related_manager(from_model, from_field_name, to_model, to_field_name)
            return manager(self.instance)
        do_not_call_in_templates = True

        def get_queryset(self):
            qs = super(RelatedManager, self).get_queryset()
            qs = qs.filter(**{"%s__contains" % to_field_name: getattr(self.instance, from_field_name)})
            return qs

        def _clear(self, commit=True):
            key = getattr(self.instance, from_field_name)
            affected = []
            for item in self.get_queryset():
                listing = getattr(item, to_field_name)
                if key in listing:
                    listing.remove(key)
                    if commit:
                        item.save()
                affected.append(item)
            return affected

        def clear(self):
            self._clear()

        def _add(self, objs, commit=True):
            key = getattr(self.instance, from_field_name)
            affected = []
            for item in objs:
                listing = getattr(item, to_field_name)
                if key not in listing:
                    listing.append(key)
                    if commit:
                        item.save()
                affected.append(item)
            return affected

        def add(self, *objs):
            self._add(objs)

        def _remove(self, objs, commit=True):
            key = getattr(self.instance, from_field_name)
            affected = []
            for item in objs:
                listing = getattr(item, to_field_name)
                if key in listing:
                    listing.remove(key)
                    if commit:
                        item.save()
                affected.append(item)
            return affected

        def remove(self, *objs):
            self._remove(objs)

        def set(self, *objs):
            """
            We defer saving until the last moment, this way,
            if it fails, nothing is comitted..
            also, this prevents groups from being saved twice.
            """
            cleared = self._clear(commit=False)
            new = self._add(objs, commit=False)
            for item in cleared:
                if item in new:
                    continue
                item.save()
            for item in new:
                item.save()
    return RelatedManager


class RelatedObjectsDescriptor(DeferredAttribute):
    def __init__(self, model, to, to_field_name, from_field_name='dn'):
        self.model = model
        self.from_field_name = from_field_name
        self.to = to
        self.to_field_name = to_field_name

    @cached_property
    def related_manager_cls(self):
        return create_related_manager(self.model, self.from_field_name, self.to, self.to_field_name)

    def __get__(self, instance, instance_type=None):
        if instance is None:
            return self
        manager = self.related_manager_cls(
            instance=instance
        )
        return manager

    def __set__(self, instance, value):
        manager = self.__get__(instance)
        manager.set(*value)


class SimpleRelationField(RelatedField):
    generate_reverse_relation = False
    requires_unique_target = False

    def __init__(self, to, to_field_name, from_field_name='dn', *args, **kwargs):
        super(SimpleRelationField, self).__init__(*args, **kwargs)
        self.rel = ManyToOneRel(self, to, to_field_name)
        self.from_field_name = from_field_name
        self.to = to
        self.to_field_name = to_field_name

    def clean(self, raw_value, obj):
        if isinstance(raw_value, (models.Manager, QuerySet)):
            raw_value = list(raw_value.all())
        return raw_value

    def get_attname_column(self):
        return self.get_attname(), None

    def contribute_to_class(self, cls, name):
        super(SimpleRelationField, self).contribute_to_class(cls, name)
        cls._meta.local_fields.remove(self)
        cls._meta.virtual_fields.append(self)
        setattr(cls, self.attname, RelatedObjectsDescriptor(cls, self.to, self.to_field_name, self.from_field_name))

    def contribute_to_related_class(self, cls, name):
        pass

    def get_path_info(self):
        opts = self.model._meta
        from_opts = self.rel.to._meta
        pathinfos = [PathInfo(from_opts, opts, (opts.pk,), self.rel, not self.unique, False)]
        return pathinfos

    def get_reverse_path_info(self):
        opts = self.model._meta
        from_opts = self.rel.to._meta
        pathinfos = [PathInfo(from_opts, opts, (opts.pk,), self.rel, not self.unique, False)]
        return pathinfos

    def get_joining_columns(self, reverse_join=False):
        return tuple()

    def get_reverse_joining_columns(self):
        return self.get_joining_columns(reverse_join=True)

    def get_extra_descriptor_filter(self, instance):
        """
        Returns an extra filter condition for related object fetching when
        user does 'instance.fieldname', that is the extra filter is used in
        the descriptor of the field.

        The filter should be either a dict usable in .filter(**kwargs) call or
        a Q-object. The condition will be ANDed together with the relation's
        joining columns.

        A parallel method is get_extra_restriction() which is used in
        JOIN and subquery conditions.
        """
        return {}

    def get_extra_restriction(self, where_class, alias, related_alias):
        """
        Returns a pair condition used for joining and subquery pushdown. The
        condition is something that responds to as_sql(compiler, connection)
        method.

        Note that currently referring both the 'alias' and 'related_alias'
        will not work in some conditions, like subquery pushdown.

        A parallel method is get_extra_descriptor_filter() which is used in
        instance.fieldname related object fetching.
        """
        return None

    def formfield(self, **kwargs):
        db = kwargs.pop('using', None)
        if isinstance(self.rel.to, six.string_types):
            raise ValueError("Cannot create form field for %r yet, because "
                             "its related model %r has not been loaded yet" %
                             (self.name, self.rel.to))
        defaults = {
            'form_class': forms.ModelChoiceField,
            'queryset': self.rel.to._default_manager.using(db),
            'to_field_name': self.rel.field_name,
        }
        defaults.update(kwargs)
        return super(SimpleRelationField, self).formfield(**defaults)


class IntField(LDAPIntegerField):
    def from_ldap(self, value, connection):
        if len(value) == 0:
            return 0
        else:
            return int(value[0])

    def get_db_prep_lookup(self, lookup_type, value, connection,
                           prepared=False):
        "Returns field's value prepared for database lookup."
        prepped = self.get_prep_lookup(lookup_type, value)
        if connection.alias != router.db_for_read(self.model):
            if isinstance(prepped, (list, tuple)):
                return prepped
        return [prepped]

    def get_db_prep_save(self, value, connection):
        if value is None:
            return None
        # This next piece of code may look odd, but it is needed for when we are
        # saving object pks across databases.. for example, using a User model
        # in ldap, that has the uidNumber bound to the id (and as such, pk) field.
        # if we then have a relation from a normal SQL database (and seriously, it
        # is a tricky thing to do.. with constraints and all), like with a foreignkey
        # .. it will save normally.
        if connection.alias != router.db_for_read(self.model):
            return str(value)
        return [str(value)]

    def get_prep_lookup(self, lookup_type, value):
        "Perform preliminary non-db specific lookup checks and conversions"
        if lookup_type in ('exact', 'gte', 'lte', 'in'):
            return value
        raise TypeError("IntegerField has invalid lookup: %s" % lookup_type)
