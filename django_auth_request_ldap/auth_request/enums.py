from django.utils.translation import ugettext_lazy as _

ZONE_ACCESS_DEFAULT = 0
ZONE_ACCESS_ALLOWED = 1
ZONE_ACCESS_DENIED = 2

ZONE_ACCESS = [
    (ZONE_ACCESS_DEFAULT, _("Default")),
    (ZONE_ACCESS_ALLOWED, _("Allowed")),
    (ZONE_ACCESS_DENIED, _("Denied")),
]
ZONE_ACCESS_DISPLAY = dict(ZONE_ACCESS)

ACTION_ACCESS = "access"
ACTION_LOGIN = "login"
ACTION_LOGOUT = "logout"
ACTION_DENIED = "access_denied"
ACTION_DISABLED = "zone_disabled"
ACTION_UNKNOWN = "zone_unknown"

LOG_ACTIONS = [
    (ACTION_ACCESS, _("Access")),
    (ACTION_LOGIN, _("Logged In")),
    (ACTION_LOGOUT, _("Logged Out")),
    (ACTION_DENIED, _("Access Denied")),
    (ACTION_DISABLED, _("Zone Disabled")),
    (ACTION_UNKNOWN, _("Zone Unknown")),
]