from django.contrib.auth.backends import ModelBackend
from django.views.decorators.debug import sensitive_variables
from django.utils import six
from django.utils.encoding import force_text

from .models import User


class LDAPBackend(ModelBackend):
    @sensitive_variables("username", "password", "user_dn", )
    def authenticate(self, username=None, password=None, **kwargs):
        if username is None or password is None:
            return None
        if not isinstance(username, six.string_types):
            return None
        username = force_text(username)
        try:
            user = User.objects.get(**{User.USERNAME_FIELD: username})
            if user.check_password(password):
                return user
        except User.DoesNotExist:
            User().check_password("")

    def get_group_permissions(self, user_obj, obj=None):
        if not isinstance(user_obj, User):
            return set()
        return user_obj.get_group_permissions()

    def get_all_permissions(self, user_obj, obj=None):
        if not isinstance(user_obj, User):
            return set()
        return user_obj.get_all_permissions()

    def get_user(self, user_id):
        if user_id is None:
            return None
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
