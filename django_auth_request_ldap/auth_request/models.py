from django.conf import settings
from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.utils import timezone

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


class ZoneUser(models.Model):
    zone = models.ForeignKey(Zone, related_name="users")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="+")
    access = models.IntegerField(_("access"), choices=ZONE_ACCESS, default=ZONE_ACCESS_DEFAULT)


class ZoneGroup(models.Model):
    zone = models.ForeignKey(Zone, related_name="groups")
    group = models.ForeignKey(settings.AUTH_GROUP_MODEL, related_name="+")
    access = models.IntegerField(_("access"), choices=ZONE_ACCESS, default=ZONE_ACCESS_DEFAULT)


class LogEntry(models.Model):
    timestamp = models.DateTimeField(default=timezone.now)
    zone = models.ForeignKey(Zone, null=True, blank=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="+")
    username = models.CharField(max_length=90)
    action = models.CharField(max_length=24, choices=LOG_ACTIONS)
    message = models.CharField(max_length=127)
    extra_data = models.CharField(max_length=127)
