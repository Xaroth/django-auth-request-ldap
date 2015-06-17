from django.contrib import auth
from django.conf import settings
from django.core import validators
from django.db import DEFAULT_DB_ALIAS, router
from django.core.mail import send_mail
from django.db import models
from django.utils.crypto import get_random_string
from django.utils.encoding import force_text, smart_text, python_2_unicode_compatible
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _
from django.utils import timezone
from ldapdb.models.fields import CharField, ListField

from .util import process_shells, CustomRDNModel
from .fields import DefaultListField, BooleanField, SimpleRelationField, DateTimeField, IntField

LDAP_DN_SUFFIX = getattr(settings, 'LDAP_DN_SUFFIX', '')

AVAILABLE_SHELLS = process_shells(getattr(settings, 'LDAP_SHELLS', [
    '/bin/bash',
    '/bin/sh',
    '/bin/csh',
    '/bin/false',
    '/usr/sbin/nologin',
]))


class SambaDomainName(CustomRDNModel):
    object_classes = ['sambaDomain', 'sambaUnixIdPool', 'top']
    gid = IntField(db_column='gidNumber')
    domain_name = CharField(db_column='sambaDomainName', primary_key=True)
    sambaSID = CharField(db_column='sambaSID')
    uid = IntField(db_column='uidNumber')

    def format_user_sid(self, uid):
        return "%s-%s" % (self.sambaSID, (uid * 2))

    def format_group_sid(self, gid):
        return "%s-%s" % (self.sambaSID, (gid * 2) + 1)

    def get_max(self, model, attr, attr_self=None):
        if attr_self is None:
            attr_self = attr
        current_max = getattr(self, attr_self)
        while True:
            try:
                model.objects.get(**{attr: current_max})
            except model.DoesNotExist:
                break
            current_max += 1
        setattr(self, attr_self, current_max + 1)
        return current_max

    def get_max_gid(self):
        return self.get_max(Group, 'gid')

    def get_max_uid(self):
        return self.get_max(User, 'id', 'uid')


@python_2_unicode_compatible
class Group(CustomRDNModel):
    dn_prefix = 'ou=groups'
    object_classes = [
        'posixGroup',
        'sambaGroupMapping',
        'djangoGroup',
        'groupOfNames',
        'top',
    ]

    def build_rdn(self):
        return 'cn=%s' % self.name

    gid = IntField(db_column='gidNumber', primary_key=True)
    name = CharField(_('name'), db_column='cn', max_length=200, unique=True)
    members = DefaultListField(db_column='member', editable=False)
    usernames = ListField(db_column='memberUid', editable=False)

    description = CharField(_('description'), db_column='description', max_length=200, default='')

    permissions = ListField(db_column='djangoPermission', blank=True, verbose_name=_('permissions'))

    _samba_sid = CharField(db_column='sambaSID', editable=False)
    _samba_group_type = CharField(db_column='sambaGroupType', default='5', editable=False)

    def check_hidden_fields(self):
        workgroup = SambaDomainName.objects.first()
        if self.gid is None:
            self.gid = workgroup.get_max_gid()
            workgroup.save()
        self._samba_sid = workgroup.format_group_sid(self.gid)
        self.usernames = list(set([x.split(',', 1)[0].split('=', 1)[-1] for x in self.members]))
        if not self.description:
            self.description = '.'

    def save(self, using=None, *args, **kwargs):
        self.check_hidden_fields()
        super(Group, self).save(using=using)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = _('group')
        verbose_name_plural = _('groups')

username_validator = validators.RegexValidator(r'^[\w.@+-]+$', _('Enter a valid username. '
                                                                 'This value may contain only letters, numbers '
                                                                 'and @/./+/-/_ characters.'), 'invalid')


@python_2_unicode_compatible
class User(CustomRDNModel):
    """
    Class for representing an Account in LDAP
    """
    dn_prefix = 'ou=people'

    object_classes = [
        'inetOrgPerson',
        'organizationalPerson',
        'person',
        'djangoUser',
        'posixAccount',
        'sambaSamAccount',
        'shadowAccount',
        'top',
    ]

    def build_rdn(self):
        return 'uid=%s' % self.username

    id = IntField(db_column='uidNumber', primary_key=True)

    group = IntField(db_column='gidNumber', default=65534)  # TODO: Choices

    home_directory = CharField(db_column='homeDirectory', blank=True)
    login_shell = CharField(db_column='loginShell', default='/bin/bash',
                            choices=AVAILABLE_SHELLS, verbose_name="Shell")

    username = CharField(_('username'), db_column='uid', unique=True,
                         help_text=_('Required. 30 characters or fewer. Letters, digits and '
                                     '@/./+/-/_ only.'),
                         validators=[username_validator, ],
                         error_messages={
                             'unique': _("A user with that username already exists."),
                             })
    first_name = CharField(_('first name'), db_column='givenName')
    last_name = CharField(_('last name'), db_column='sn')
    password = CharField(_('password'), db_column='userPassword')

    email = CharField(_('email address'), db_column='mail')

    is_staff = BooleanField(_('staff status'), db_column='djangoStaff', default=False,
                            help_text=_('Designates whether the user can log into this admin '
                                        'site.'))
    is_superuser = BooleanField(_('superuser status'), db_column='djangoSuper', default=False,
                                help_text=_('Designates that this user has all permissions without '
                                            'explicitly assigning them.'))
    is_active = BooleanField(_('active'), db_column='djangoActive', default=True,
                             help_text=_('Designates whether this user should be treated as '
                                         'active. Unselect this instead of deleting accounts.'))

    date_joined = DateTimeField(_('date joined'), db_column='djangoCreated', default=timezone.now)
    last_login = DateTimeField(_('last login'), db_column='djangoLastLogon', default=timezone.now)

    groups = SimpleRelationField(Group, 'members', verbose_name=_('groups'),
                                 help_text=_('The groups this user belongs to. A user will '
                                             'get all permissions granted to each of '
                                             'their groups.'))

    user_permissions = ListField(db_column='djangoPermission', blank=True, verbose_name=_('user permissions'),
                                 help_text=_('Specific permissions for this user.'))

    ssh_public_keys = ListField(db_column='sshPublicKey', blank=True)

    # hidden fields:
    _full_name = CharField(db_column='cn', blank=True, editable=False)
    _real_name = CharField(db_column='displayName', blank=True, editable=False)

    _member_of = ListField(db_column='memberOf', blank=True, editable=False)

    _samba_sid = CharField(db_column='sambaSID', blank=True, unique=True, editable=False)
    _samba_flags = CharField(db_column='sambaAcctFlags', default='[U]', editable=False)
    _samba_pw_lastset = IntField(db_column='sambaPwdLastSet', default=1, editable=False)
    _samba_pw_mustchange = IntField(db_column='sambaPwdMustChange', default=9999999999999, editable=False)
    _samba_pw_canchange = IntField(db_column='sambaPwdCanChange', default=0, editable=False)

    _samba_nt_password = CharField(db_column='sambaNTPassword', blank=True,
                                   help_text="md4 (Windows NT) encoded 'password',"
                                   " use the <a href=\"password/\">change password form</a>.",
                                   editable=False)

    def __str__(self):
        return self._full_name

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['email', ]

    def check_hidden_fields(self):
        workgroup = SambaDomainName.objects.all()[0]
        if self.id is None:
            self.id = workgroup.get_max_uid()
            workgroup.save()
        self._full_name = ('%s %s' % (self.first_name, self.last_name)).strip()
        self._real_name = self._full_name
        self._samba_sid = workgroup.format_user_sid(self.id)

    def check_values(self):
        password_made_inactive = self.password.startswith('!')
        if self.is_active == password_made_inactive:
            if self.is_active:
                self.password = self.password.lstrip('!')
                self._samba_nt_password = self._samba_nt_password.lstrip('!')
            else:
                self.password = '!' + self.password
                self._samba_nt_password = '!' + self._samba_nt_password
        if not self.home_directory:
            self.home_directory = '/home/%s' % self.username

    def save(self, using=None, *args, **kwargs):
        self.check_hidden_fields()
        self.check_values()
        super(User, self).save(using=using)

    def get_username(self):
        return getattr(self, self.USERNAME_FIELD)

    def is_anonymous(self):
        return False

    def is_authenticated(self):
        return True

    def get_full_name(self):
        return self._full_name

    def get_short_name(self):
        "Returns the short name for the user."
        return self.first_name

    def email_user(self, subject, message, from_email=None, **kwargs):
        """
        Sends an email to this User.
        """
        send_mail(subject, message, from_email, [self.email], **kwargs)

    @classmethod
    def hash_password(cls, raw_password):
        from os import urandom
        from hashlib import sha1
        from base64 import encodestring
        salt = urandom(4)
        hashed = sha1(raw_password)
        hashed.update(salt)
        return '{SSHA}%s' % encodestring(hashed.digest() + salt).rstrip()

    @classmethod
    def hash_ntpassword(cls, raw_password):
        import hashlib
        md4 = hashlib.new('md4', raw_password.encode('utf-16le')).hexdigest().upper()
        return md4

    def set_password(self, raw_password):
        if raw_password is None:
            self.password = '0'
            self._samba_nt_password = '0'
        self.password = User.hash_password(raw_password)
        self._samba_nt_password = User.hash_ntpassword(raw_password)

    def check_password(self, password):
        password = force_text(password)
        db_alias = router.db_for_read(self.__class__) or DEFAULT_DB_ALIAS
        import ldap
        conn = ldap.initialize(settings.DATABASES[db_alias]['NAME'])
        try:
            conn.bind_s(self.dn, password)
        except Exception:
            return False
        return True

    def get_group_permissions(self, obj=None):
        permissions = getattr(self, '_group_perm_cache', None)
        if not permissions:
            permissions = set()
            for group in self.groups.all():
                permissions.update(group.permissions)
            self._group_perm_cache = permissions
        return permissions

    def get_user_permissions(self, obj=None):
        permissions = getattr(self, '_user_perm_cache', None)
        if not permissions:
            permissions = set()
            permissions.update(self.permissions)
            self._user_perm_cache = permissions
        return permissions

    def get_all_permissions(self, obj=None):
        permissions = getattr(self, '_perm_cache', None)
        if not permissions:
            permissions = set()
            permissions.update(self.get_user_permissions(obj))
            permissions.update(self.get_group_permissions(obj))
            self._perm_cache = permissions
        return permissions

    def has_perm(self, perm, obj=None):
        if not self.is_active:
            return False
        if self.is_superuser:
            return True
        return perm in self.get_all_permissions()

    def has_perms(self, perm_list, obj=None):
        for perm in perm_list:
            if not self.has_perm(perm, obj):
                return False
        return True

    def has_module_perms(self, app_label):
        if not self.is_active:
            return False
        if self.is_superuser:
            return True
        for perm in self.get_all_permissions():
            if perm[:perm.index('.')] == app_label:
                return True
        return False

    class Meta:
        verbose_name = _('user')
        verbose_name_plural = _('users')
