from django.conf import settings
from django.core.cache import cache
from django.db import models
from django.utils import timezone
from django.utils.encoding import python_2_unicode_compatible, force_text
from django.utils.translation import ugettext_lazy as _

from operator import attrgetter

from .enums import (ZONE_ACCESS_DEFAULT, ZONE_ACCESS_ALLOWED, ZONE_ACCESS_DENIED, ZONE_ACCESS, ZONE_ACCESS_DISPLAY,
                    ACTION_ACCESS, ACTION_DENIED, ACTION_LOGIN, ACTION_LOGOUT, ACTION_DISABLED, ACTION_UNKNOWN,
                    LOG_ACTIONS)

import time

ZONE_ACCESS_CACHE_TIME = getattr(settings, "ZONE_ACCESS_CACHE_TIME", 0)
ZONE_ACCESS_LOG_CACHED = getattr(settings, "ZONE_ACCESS_LOG_CACHED", False)
ZONE_ACCESS_ALLOWED_LOG_THRESHOLD = getattr(settings, "ZONE_ACCESS_ALLOWED_LOG_THRESHOLD", 0)
ZONE_ACCESS_DEFAULT_RESPONSE = getattr(settings, "ZONE_ACCESS_DEFAULT_RESPONSE", ZONE_ACCESS_DENIED)

ACTIONS_FOR_ACCESS = {
    ZONE_ACCESS_ALLOWED: ACTION_ACCESS,
    ZONE_ACCESS_DENIED: ACTION_DENIED,
}
ACTIONS_FOR_ACCESS[ZONE_ACCESS_DEFAULT] = ACTIONS_FOR_ACCESS.get(ZONE_ACCESS_DEFAULT_RESPONSE)


@python_2_unicode_compatible
class Zone(models.Model):
    name = models.CharField(max_length=128)
    code = models.SlugField(max_length=128)
    access = models.IntegerField(_("access"), choices=ZONE_ACCESS, default=ZONE_ACCESS_DEFAULT)
    enabled = models.BooleanField(default=True)

    def access_for_user(self, user):
        key = 'auth_request__access_for_user__%s_%s' % (self.pk, user.pk)
        cached = cache.get(key, None)
        if cached is not None and ZONE_ACCESS_CACHE_TIME:
            return cached
        groups = user.groups.all()
        grouprules = list(self.groups.filter(group_id__in=[g.pk for g in groups]))
        userrules = list(self.users.filter(user=user))
        all_rules = sorted(grouprules + userrules, key=attrgetter('order'))

        access = self.access
        for rule in all_rules:
            if rule.access == ZONE_ACCESS_DEFAULT:
                continue
            access = rule.access
        data = (self.access, len(grouprules), len(userrules), access)
        if ZONE_ACCESS_CACHE_TIME:
            cache.set(key, data + (time.time(),), ZONE_ACCESS_CACHE_TIME)
        return data + (False,)

    def log_message(self, user, action, message, extra_data=None):
        entry = LogEntry(
            zone=self,
            user=user,
            username=getattr(user, user.USERNAME_FIELD),
            action=action,
            message=message,
            extra_data=extra_data or '')
        entry.save()
        return entry

    def log_access(self, user, cached=False):
        if ZONE_ACCESS_ALLOWED_LOG_THRESHOLD:
            key = 'zone__log_access__%s_%s' % (self.pk, user.pk)
            if cache.get(key, False):
                return None
            cache.set(key, True, ZONE_ACCESS_ALLOWED_LOG_THRESHOLD)
        message = "user requested access"
        return self.log_message(user, ACTION_ACCESS, message, extra_data=("cached response" if cached else ''))

    def log_denied(self, user, cached=False):
        message = "user denied access"
        return self.log_message(user, ACTION_DENIED, message, extra_data=("cached response" if cached else ''))

    def log_disabled(self, user, cached=False):
        message = "user requested access to a disabled zone"
        return self.log_message(user, ACTION_DISABLED, message, extra_data=("cached response" if cached else ''))

    def log_login(self, user, cached=False):
        message = "user logged in"
        return self.log_message(user, ACTION_ACCESS, message, extra_data=getattr(user, user.USERNAME_FIELD))

    def log_logout(self, user, cached=False):
        message = "user logged out"
        return self.log_message(user, ACTION_ACCESS, message, extra_data=getattr(user, user.USERNAME_FIELD))

    def log_by_action(self, user, action, cached=False):
        handlers = {
            ACTION_ACCESS: self.log_access,
            ACTION_DENIED: self.log_denied,
            ACTION_DISABLED: self.log_disabled,
            ACTION_LOGIN: self.log_login,
            ACTION_LOGOUT: self.log_logout,
        }
        if action in handlers:
            return handlers[action](user, cached)
        return None

    @classmethod
    def process_access_request(self, zone_key, user):
        key = 'auth_request__process__%s_%s' % (zone_key, user.pk)

        def _stor(action, response, zone):
            print(repr((action, response, zone)))
            cache.set(key, (action, response), ZONE_ACCESS_CACHE_TIME)
            if zone:
                zone.log_by_action(user, action, False)
            return action, response

        cached = cache.get(key, None)
        if cached is not None and ZONE_ACCESS_CACHE_TIME:
            action, response = cached
            if action == ACTION_UNKNOWN:
                return action, response
            if ZONE_ACCESS_LOG_CACHED:
                zone = Zone.objects.get(code=zone_key)
                zone.log_by_action(user, action, cached=True)
            return action, response

        try:
            zone = Zone.objects.get(code=zone_key)
        except Zone.DoesNotExist:
            return _stor(ACTION_UNKNOWN, ZONE_ACCESS_DEFAULT_RESPONSE, None)

        if not zone.enabled:
            return _stor(ACTION_DISABLED, ZONE_ACCESS_DENIED, zone)

        default_access, grouprules, userrules, response, cached = zone.access_for_user(user)
        print(repr((default_access, grouprules, userrules, response, cached)))

        return _stor(
            ACTIONS_FOR_ACCESS[response],
            response,
            zone
        )

    @classmethod
    def process_login(self, zone_key, user):
        try:
            zone = Zone.objects.get(code=zone_key)
        except Zone.DoesNotExist:
            print("no zone")
            return False

        if not zone.enabled:
            print("zone not enabled")
            return False
        default_access, grouprules, userrules, response, cached = zone.access_for_user(user)

        print(repr((default_access, grouprules, userrules, response, cached)))

        if response == ZONE_ACCESS_ALLOWED:
            zone.log_by_action(user, ACTION_LOGIN)
            return True
        return False

    def __str__(self):
        return self.name


@python_2_unicode_compatible
class ZoneUser(models.Model):
    zone = models.ForeignKey(Zone, related_name="users")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="+")
    access = models.IntegerField(_("access"), choices=ZONE_ACCESS, default=ZONE_ACCESS_DEFAULT)
    order = models.IntegerField(_("order of importance"), default=10)

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

    class Meta:
        ordering = ['order']

    def __repr__(self):
        return "<%s: %r (%s)>" % (self.__class__.__name__, self.group, ZONE_ACCESS_DISPLAY.get(self.access))

    def __str__(self):
        return force_text(self.group)


@python_2_unicode_compatible
class LogEntry(models.Model):
    timestamp = models.DateTimeField(default=timezone.now)
    zone = models.ForeignKey(Zone, null=True, blank=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="+")
    username = models.CharField(max_length=90)
    action = models.CharField(max_length=24, choices=LOG_ACTIONS)
    message = models.CharField(max_length=127)
    extra_data = models.CharField(max_length=127)

    class Meta:
        ordering = ['-timestamp']
        verbose_name = _("Log Entry")
        verbose_name_plural = _("Log Entries")

    def __str__(self):
        return force_text(self.timestamp)
