from django.conf import settings
from django.core.cache import cache
from django.db import models
from django.utils import timezone
from django.utils.encoding import python_2_unicode_compatible, force_text
from django.utils.translation import ugettext_lazy as _

from operator import attrgetter

from .enums import (ZONE_ACCESS_DEFAULT, ZONE_ACCESS_ALLOWED, ZONE_ACCESS_DENIED, ZONE_ACCESS, ZONE_ACCESS_DISPLAY,
                    ACTION_ACCESS, ACTION_DENIED, ACTION_LOGIN, ACTION_LOGOUT, ACTION_DISABLED, ACTION_UNKNOWN,
                    ACCESS_DISPLAY)

import time

import logging
logger = logging.getLogger(__name__)

ZONE_ACCESS_CACHE_TIME = getattr(settings, "ZONE_ACCESS_CACHE_TIME", 0)
ZONE_ACCESS_LOG_CACHED = getattr(settings, "ZONE_ACCESS_LOG_CACHED", 0)
ZONE_ACCESS_DEFAULT_RESPONSE = getattr(settings, "ZONE_ACCESS_DEFAULT_RESPONSE", ZONE_ACCESS_DENIED)


class AccessMatrix(object):
    def __init__(self, zone, user, group_rules, user_rules):
        self.zone = zone
        self.user = user
        self.group_rules = group_rules
        self.user_rules = user_rules

    @property
    def user_pk(self):
        return self.user.pk if self.user.is_authenticated() else 0

    def _cache_matrix(self, key, rules):
        key = '_cache_matrix_%d_%d_%s' % (self.zone.pk, self.user_pk, key)
        if ZONE_ACCESS_CACHE_TIME:
            data = cache.get(key, None)
            if data is not None:
                setattr(self, key, data[0])
                return data
        data = getattr(self, key, None)
        if data is not None:
            return data, None
        data = self.process_rules(rules)
        setattr(self, key, data)
        if ZONE_ACCESS_CACHE_TIME:
            cache.set(key, (data, time.time()), ZONE_ACCESS_CACHE_TIME)
        return data, None

    @property
    def rules(self):
        return self.group_rules + self.user_rules

    def process_rules(self, rules):
        print("process_rules")
        rules = sorted(rules, key=attrgetter("order"))
        access = self.zone.access
        logger.debug("Default access for matrix: %s", ZONE_ACCESS_DISPLAY[access])
        for rule in rules:
            if rule.access != ZONE_ACCESS_DEFAULT:
                access = rule.access
            logger.debug(
                "%d: Applied rule for %s %s: %s, new active access: %s",
                rule.order,
                rule.object.__class__.__name__,
                rule.object,
                ZONE_ACCESS_DISPLAY[rule.access],
                ZONE_ACCESS_DISPLAY[access]
            )
        logger.debug("Done processing access: %s", ZONE_ACCESS_DISPLAY[access])
        return access

    @property
    def allowed(self):
        return self._cache_matrix('all', self.rules)

    @property
    def allowed_by_group(self):
        return self._cache_matrix('group', self.group_rules)

    @property
    def allowed_by_user(self):
        return self._cache_matrix('user', self.user_rules)

    def __bool__(self):
        return self.allowed
    __nonzero__ = __bool__

    def __repr__(self):
        return "<AccessMatrix: %r: %r>" % (self.zone, self.user)


@python_2_unicode_compatible
class Zone(models.Model):
    name = models.CharField(max_length=128)
    code = models.SlugField(max_length=128)
    access = models.IntegerField(_("access"), choices=ZONE_ACCESS, default=ZONE_ACCESS_DEFAULT)
    enabled = models.BooleanField(default=True)

    def for_user(self, user):
        if not user.is_authenticated():
            return AccessMatrix(self, user, [], [])
        groups = user.groups.all()
        group_rules = list(self.groups.filter(group_id__in=[g.pk for g in groups]))
        user_rules = list(self.users.filter(user=user))
        return AccessMatrix(self, user, group_rules, user_rules)

    @classmethod
    def process_request(self, user, zone_key):
        if not user.is_authenticated():
            user_pk = 0
        else:
            user_pk = user.pk
        key = 'process_%s_%s' % (zone_key, user_pk)

        if ZONE_ACCESS_CACHE_TIME:
            data = cache.get(key, None)
            if data is not None:
                return data

        try:
            zone = Zone.objects.get(code=zone_key)
        except Zone.DoesNotExist:
            return ACTION_UNKNOWN, None

        data = zone.process(user)

        if ZONE_ACCESS_CACHE_TIME:
            cache.set(key, (data, time.time()), ZONE_ACCESS_CACHE_TIME)
        return data, None

    def do_log(self, matrix, action):
        allowed, cached_at = matrix.allowed
        user_pk = matrix.user_pk
        key = 'do_log_%s_%s_%s' % (user_pk, matrix.zone.pk, allowed)
        username = "<ANONYMOUS>" if user_pk == 0 else getattr(matrix.user, matrix.user.USERNAME_FIELD)
        if ZONE_ACCESS_LOG_CACHED:
            if cache.get(key, None):
                return
            cache.set(key, True, ZONE_ACCESS_LOG_CACHED)
        logger.info("request to zone '%s' resulted in '%s'(%s) / '%s'(%s) for user '%s'(%d)",
                    self.code,
                    ZONE_ACCESS_DISPLAY[allowed],
                    allowed,
                    ACCESS_DISPLAY[action],
                    action,
                    username,
                    user_pk,
                    )

    def process(self, user):
        if not self.enabled:
            return ACTION_DISABLED

        matrix = self.for_user(user)

        def _log(action):
            self.do_log(matrix, action)
            return action

        access, cached_at = matrix.allowed
        if access == ZONE_ACCESS_DEFAULT:
            access = ZONE_ACCESS_DEFAULT_RESPONSE

        if access == ZONE_ACCESS_DENIED:
            if not user.is_authenticated():
                return _log(ACTION_LOGIN)
            return _log(ACTION_DENIED)

        if access == ZONE_ACCESS_DENIED:
            return _log(ACTION_DENIED)

        return _log(ACTION_ACCESS)

    def __str__(self):
        return self.name


@python_2_unicode_compatible
class ZoneUser(models.Model):
    zone = models.ForeignKey(Zone, related_name="users")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="+")
    access = models.IntegerField(_("access"), choices=ZONE_ACCESS, default=ZONE_ACCESS_DEFAULT)
    order = models.IntegerField(_("order of importance"), default=10)

    @property
    def object(self):
        return self.user

    class Meta:
        ordering = ['order']

    def __repr__(self):
        return "<%s: %r (%s)>" % (self.__class__.__name__, self.user, ZONE_ACCESS_DISPLAY.get(self.access))

    def __str__(self):
        return force_text(self.user)


@python_2_unicode_compatible
class ZoneGroup(models.Model):
    zone = models.ForeignKey(Zone, related_name="groups")
    group = models.ForeignKey(settings.AUTH_GROUP_MODEL, related_name="+")
    access = models.IntegerField(_("access"), choices=ZONE_ACCESS, default=ZONE_ACCESS_DEFAULT)
    order = models.IntegerField(_("order of importance"), default=10)

    @property
    def object(self):
        return self.group

    class Meta:
        ordering = ['order']

    def __repr__(self):
        return "<%s: %r (%s)>" % (self.__class__.__name__, self.group, ZONE_ACCESS_DISPLAY.get(self.access))

    def __str__(self):
        return force_text(self.group)
