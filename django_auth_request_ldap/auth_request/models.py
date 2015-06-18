from django.conf import settings
from django.core.cache import cache
from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.utils import timezone

from operator import attrgetter

ZONE_ACCESS_CACHE_TIME = getattr(settings, "ZONE_ACCESS_CACHE_TIME", 60)

ZONE_ACCESS_DEFAULT = 0
ZONE_ACCESS_ALLOWED = 1
ZONE_ACCESS_DENIED = 2

ZONE_ACCESS = [
    (ZONE_ACCESS_DEFAULT, _("Default")),
    (ZONE_ACCESS_ALLOWED, _("Allowed")),
    (ZONE_ACCESS_DENIED, _("Denied")),
]

ACTION_ACCESS = "access"
ACTION_LOGIN = "login"
ACTION_LOGOUT = "logout"
ACTION_DENIED = "access_denied"

LOG_ACTIONS = [
    (ACTION_ACCESS, _("Access")),
    (ACTION_LOGIN, _("Logged In")),
    (ACTION_LOGOUT, _("Logged Out")),
    (ACTION_DENIED, _("Access Denied")),
]


class Zone(models.Model):
    name = models.CharField(max_length=128)
    code = models.SlugField(max_length=128)
    access = models.IntegerField(_("access"), choices=ZONE_ACCESS, default=ZONE_ACCESS_DEFAULT)
    enabled = models.BooleanField(default=True)

    def access_for_user(self, user):
        key = 'auth_request__access_for_user__%s' % user.pk
        cached = cache.get(key, None)
        if cached is not None:
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
        cache.set(key, access, ZONE_ACCESS_CACHE_TIME)
        return access


class ZoneUser(models.Model):
    zone = models.ForeignKey(Zone, related_name="users")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="+")
    access = models.IntegerField(_("access"), choices=ZONE_ACCESS, default=ZONE_ACCESS_DEFAULT)
    order = models.IntegerField(_("order of importance"), default=10)

    class Meta:
        ordering = ['order']


class ZoneGroup(models.Model):
    zone = models.ForeignKey(Zone, related_name="groups")
    group = models.ForeignKey(settings.AUTH_GROUP_MODEL, related_name="+")
    access = models.IntegerField(_("access"), choices=ZONE_ACCESS, default=ZONE_ACCESS_DEFAULT)
    order = models.IntegerField(_("order of importance"), default=10)

    class Meta:
        ordering = ['order']


class LogEntry(models.Model):
    timestamp = models.DateTimeField(default=timezone.now)
    zone = models.ForeignKey(Zone, null=True, blank=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="+")
    username = models.CharField(max_length=90)
    action = models.CharField(max_length=24, choices=LOG_ACTIONS)
    message = models.CharField(max_length=127)
    extra_data = models.CharField(max_length=127)

    class Meta:
        ordering = ['timestamp']
