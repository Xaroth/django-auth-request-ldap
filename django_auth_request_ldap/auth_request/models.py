from django.conf import settings
from django.db import models
from django.utils.translation import ugettext_lazy as _

ZONE_ACCESS_DEFAULT = 0
ZONE_ACCESS_ALLOWED = 1
ZONE_ACCESS_DENIED = 2

ZONE_ACCESS = [
    (ZONE_ACCESS_DEFAULT, _("Default")),
    (ZONE_ACCESS_ALLOWED, _("Allowed")),
    (ZONE_ACCESS_DENIED, _("Denied")),
]


class Zone(models.Model):
    name = models.CharField(max_length=128)
    code = models.SlugField(max_length=128)
    enabled = models.BooleanField(default=True)


class ZoneUser(models.Model):
    zone = models.ForeignKey(Zone)
    user = models.ForeignKey(settings.AUTH_USER_MODEL)
    access = models.IntegerField(_("access"), choices=ZONE_ACCESS, default=ZONE_ACCESS_DEFAULT)


class ZoneGroup(models.Model):
    zone = models.ForeignKey(Zone)
    group = models.ForeignKey(settings.AUTH_GROUP_MODEL)
    access = models.IntegerField(_("access"), choices=ZONE_ACCESS, default=ZONE_ACCESS_DEFAULT)
