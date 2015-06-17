from django import forms
from django.conf import settings
from django.contrib.auth.forms import UserCreationForm as DJ_UserCreationForm
from django.contrib.admin.widgets import FilteredSelectMultiple
from django.utils.translation import ugettext as __, ugettext_lazy as _
from django.utils.encoding import smart_str
from django.utils.safestring import mark_safe
from django.forms.util import flatatt

from .models import User, Group
from .utils import PermissionsIterator

try:
    from suit.widgets import SuitSplitDateTimeWidget
    SUIT_ENABLED = 'suit' in settings.INSTALLED_APPS
except:
    SUIT_ENABLED = False

if SUIT_ENABLED:
    user_widgets = {
        'last_login': SuitSplitDateTimeWidget,
        'date_joined': SuitSplitDateTimeWidget,
    }
else:
    user_widgets = {}


class ReadOnlyPasswordHashWidget(forms.Widget):
    def render(self, name, value, attrs):
        encoded = smart_str(value)
        final_attrs = self.build_attrs(attrs)

        if '{SSHA}' not in encoded:
            return "None"
        data = encoded.split('}', 1)[1]
        dlen = len(data) / 8
        data = data[0:dlen] + ('*' * 8) + data[-dlen:]
        is_active = not encoded.startswith('!')
        summary = "<strong>%(type)s</strong>: %(value)s. <strong>%(active)s</strong>: %(is_active)s" % {
            'type': "SSHA", "value": data,
            'active': __("Active"), "is_active": __("Yes") if is_active else __("No"),
        }
        return mark_safe("<div%(attrs)s>%(summary)s</div>" % {"attrs": flatatt(final_attrs), "summary": summary})


class ReadOnlyPasswordHashField(forms.Field):
    widget = ReadOnlyPasswordHashWidget

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("required", False)
        super(ReadOnlyPasswordHashField, self).__init__(*args, **kwargs)


class GroupEditForm(forms.ModelForm):
    permissions = forms.MultipleChoiceField(choices=PermissionsIterator(), required=False,
                                            widget=FilteredSelectMultiple('permissions', False, attrs={'rows': 10}))

    def __init__(self, *args, **kwargs):
        instance = kwargs.get('instance', None)
        super(GroupEditForm, self).__init__(*args, **kwargs)
        if instance is None:
            return


class UserChangeForm(forms.ModelForm):
    groups = forms.ModelMultipleChoiceField(queryset=Group.objects.all(), required=False,
                                            widget=FilteredSelectMultiple('groups', False, attrs={'rows': '10'}))
    permissions = forms.MultipleChoiceField(choices=PermissionsIterator(), required=False,
                                            widget=FilteredSelectMultiple('permissions', False, attrs={'rows': 10}))
    password = ReadOnlyPasswordHashField(label=_("Password"),
                                         help_text=_("Raw passwords are not stored, so there is no way to see "
                                                     "this user's password, but you can change the password "
                                                     "using <a href=\"password/\">this form</a>."))

    def __init__(self, *args, **kwargs):
        instance = kwargs.get('instance', None)
        super(UserChangeForm, self).__init__(*args, **kwargs)
        if instance is None:
            return
        glist = instance.groups.all()
        self.fields['groups'].initial = glist
        self.initial['groups'] = glist

    def clean_password(self):
        # Regardless of what the user provides, return the initial value.
        # This is done here, rather than on the field, because the
        # field does not have access to the initial value
        return self.initial["password"]

    class Meta:
        fields = '__all__'
        model = User
        widgets = user_widgets


class UserCreationForm(DJ_UserCreationForm):
    """
    A form that creates a user, with no privileges, from the given username and password.
    """
    email = forms.EmailField(label=_("E-mail"), max_length=75)
    groups = forms.ModelMultipleChoiceField(queryset=Group.objects.all(), required=False,
                                            widget=FilteredSelectMultiple('groups', False, attrs={'rows': '10'}))

    def clean_username(self):
        username = self.cleaned_data["username"]
        try:
            User.objects.get(**{User.USERNAME_FIELD: username})
        except User.DoesNotExist:
            return username
        raise forms.ValidationError(
            self.error_messages['duplicate_username'],
            code='duplicate_username',
        )


class GroupCreationForm(forms.ModelForm):
    permissions = forms.MultipleChoiceField(choices=PermissionsIterator(), required=False,
                                            widget=FilteredSelectMultiple('permissions', False, attrs={'rows': 10}))
    class Meta:
        fields = ['name', 'permissions']
        model = Group
