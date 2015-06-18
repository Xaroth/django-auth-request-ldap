from django.contrib import admin
from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.contrib.auth.forms import AdminPasswordChangeForm
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.contrib.auth.models import User as DJUser, Group as DJGroup
from django.contrib.admin.models import LogEntryManager, LogEntry

from .models import User, Group
from .forms import UserCreationForm, UserChangeForm, GroupEditForm, GroupCreationForm


class LogEntryQuerySet(models.QuerySet):
    def select_related(self, *args):
        prefetch_user = False
        if 'user' in args:
            args = [x for x in args if x != 'user']
            prefetch_user = True
        elif len(args) == 0:
            args = ['content_type']
            prefetch_user = True
        qs = super(LogEntryQuerySet, self).select_related(*args)
        if prefetch_user:
            qs = qs.prefetch_related('user')
        return qs


class LogEntryQuerySetManager(LogEntryManager.from_queryset(LogEntryQuerySet)):
    pass
LogEntry.objects = LogEntryQuerySetManager()
LogEntry.objects.contribute_to_class(LogEntry, 'objects')


class GroupAdmin(admin.ModelAdmin):
    search_fields = ('name',)
    ordering = ('name',)
    readonly_fields = ['dn', 'name']
    add_readonly_fields = ['dn']
    add_form = GroupCreationForm
    form = GroupEditForm
    fieldsets = (
        (None, {'fields': ('gid', 'name',)}),
        (_('Permissions'), {'fields': ('permissions',)}),
    )
    add_fieldsets = (
        (None, {'fields': ('name',)}),
        (_('Permissions'), {'fields': ('permissions',)}),
    )

    def get_fieldsets(self, request, obj=None):
        if not obj:
            return self.add_fieldsets
        return super(GroupAdmin, self).get_fieldsets(request, obj)

    def get_readonly_fields(self, request, obj):
        if not obj:
            return self.add_readonly_fields
        return self.readonly_fields

    def get_form(self, request, obj=None, **kwargs):
        """
        Use special form during user creation
        """
        defaults = {}
        if obj is None:
            defaults.update({
                'form': self.add_form,
                'fields': admin.utils.flatten_fieldsets(self.add_fieldsets),
            })
        defaults.update(kwargs)
        return super(GroupAdmin, self).get_form(request, obj, **defaults)


class UserAdmin(DjangoUserAdmin):
    add_form_template = 'admin/auth/user/add_form.html'
    change_user_password_template = None
    fieldsets = (
        (None, {'fields': ('username', 'password',)}),
        (_('Personal info'), {'fields': ('first_name', 'last_name', 'email',)}),
        (_('Permissions'), {'fields': ('is_active', 'is_staff', 'is_superuser',
                                       'groups', 'permissions',)}),
        (_('Important dates'), {'fields': ('last_login', 'date_joined',)}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'password1', 'password2',)}),
        (_('Personal info'), {'fields': ('first_name', 'last_name', 'email',)}),
    )

    add_form = UserCreationForm
    form = UserChangeForm
    change_password_form = AdminPasswordChangeForm
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff')
    list_filter = ('is_staff', 'is_superuser', 'groups')
    search_fields = ('username', 'first_name', 'last_name', 'email')
    ordering = ('username',)
    readonly_fields = ['dn', ]
    filter_horizontal = ()

    def get_fieldsets(self, request, obj=None):
        if not obj:
            return self.add_fieldsets
        return super(UserAdmin, self).get_fieldsets(request, obj)

    def get_form(self, request, obj=None, **kwargs):
        """
        Use special form during user creation
        """
        defaults = {}
        if obj is None:
            defaults.update({
                'form': self.add_form,
                'fields': admin.utils.flatten_fieldsets(self.add_fieldsets),
            })
        defaults.update(kwargs)
        return super(UserAdmin, self).get_form(request, obj, **defaults)

    def get_urls(self):
        from django.conf.urls import patterns
        return patterns('',
                        (r'^([^\/]+)/password/$',
                         self.admin_site.admin_view(self.user_change_password))
                        ) + super(UserAdmin, self).get_urls()

admin.site.register(User, UserAdmin)
admin.site.register(Group, GroupAdmin)

for model in (DJUser, DJGroup):
    if model in admin.site._registry:
        admin.site.unregister(model)
