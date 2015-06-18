from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _


class AuthRequestConfig(AppConfig):
    name = 'auth_request'
    verbose_name = _("Auth Request")
