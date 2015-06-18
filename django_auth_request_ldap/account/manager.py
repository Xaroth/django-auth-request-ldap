from django.db import models


class LDAPQuerySet(models.QuerySet):
    def using(self, alias):
        return self


class LDAPManager(models.Manager.from_queryset(LDAPQuerySet)):
    pass
