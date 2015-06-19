from django import forms
from django.conf import settings
from django.contrib import admin
from django.apps import apps as django_apps
from .models import Zone, ZoneUser, ZoneGroup, LogEntry
from django_select2 import AutoModelSelect2Field, AutoHeavySelect2Widget

User = django_apps.get_model(settings.AUTH_USER_MODEL)
Group = django_apps.get_model(settings.AUTH_GROUP_MODEL)


class UserChoices(AutoModelSelect2Field):
    queryset = User.objects
    search_fields = ['username__icontains']


class GroupChoices(AutoModelSelect2Field):
    queryset = Group.objects
    search_fields = ['name__icontains']


class ZoneUserForm(forms.ModelForm):
    user_verbose_name = User._meta.verbose_name
    user = UserChoices(
        label=user_verbose_name.capitalize(),
        widget=AutoHeavySelect2Widget(
            select2_options={
                'width': '220px',
                'placeholder': 'Find %s ...' % user_verbose_name
            }
        )
    )

    class Meta:
        model = ZoneUser
        fields = '__all__'

    class Media:
        css = {
            'all': ('django_select2/css/select2.min.css',)
        }


class ZoneGroupForm(forms.ModelForm):
    group_verbose_name = Group._meta.verbose_name
    group = GroupChoices(
        label=group_verbose_name.capitalize(),
        widget=AutoHeavySelect2Widget(
            select2_options={
                'width': '220px',
                'placeholder': 'Find %s ...' % group_verbose_name
            }
        )
    )

    class Meta:
        model = ZoneGroup
        fields = '__all__'

    class Media:
        css = {
            'all': ('django_select2/css/select2.min.css',)
        }


class ZoneGroupAdmin(admin.TabularInline):
    model = ZoneGroup
    form = ZoneGroupForm
    min_num = 0
    extra = 3


class ZoneUserAdmin(admin.TabularInline):
    model = ZoneUser
    form = ZoneUserForm
    min_num = 0
    extra = 3


class ZoneAdmin(admin.ModelAdmin):
    prepopulated_fields = {'code': ("name",)}
    inlines = [
        ZoneGroupAdmin,
        ZoneUserAdmin,
    ]


class LogEntryAdmin(admin.ModelAdmin):
    list_display = [
        'timestamp',
        'zone',
        'user',
        'username',
        'action',
        'message',
        'extra_data',
    ]
    list_select_related = ['zone']
    list_filter = [
        'zone',
        'username',
        'action',
    ]

    readonly_fields = [
        'timestamp',
        'zone',
        'user',
        'username',
        'action',
        'message',
        'extra_data',
    ]

    def get_queryset(self, request):
        qs = super(LogEntryAdmin, self).get_queryset(request)
        return qs.prefetch_related('user')

admin.site.register(Zone, ZoneAdmin)
admin.site.register(LogEntry, LogEntryAdmin)
