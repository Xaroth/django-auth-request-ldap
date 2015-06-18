"""
Django settings for django_auth_request_ldap project.

Generated by 'django-admin startproject' using Django 1.8.2.

For more information on this file, see
https://docs.djangoproject.com/en/1.8/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.8/ref/settings/
"""

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
import os
from .local_settings import *

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.8/howto/deployment/checklist/

ALLOWED_HOSTS = ['*']


# Application definition

INSTALLED_APPS = (
    'account',
    'suit',
    'auth_request',
    'django_select2',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
)

MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.auth.middleware.SessionAuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django.middleware.security.SecurityMiddleware',
)

ROOT_URLCONF = 'django_auth_request_ldap.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'django_auth_request_ldap.wsgi.application'

AUTHENTICATION_BACKENDS = (
    'account.backends.LDAPBackend',
)

AUTH_USER_MODEL = "account.User"
AUTH_GROUP_MODEL = "account.Group"


# Database
# https://docs.djangoproject.com/en/1.8/ref/settings/#databases

DATABASE_ROUTERS = [
    'account.utils.Router',
]

DATABASES = {
    'default': AUDIT_DATABASE,
    'ldap': {
        'ENGINE':   'ldapdb.backends.ldap',
        'NAME':     'ldapi:///',
        'USER':     LDAP_ADMIN_DN,
        'PASSWORD': LDAP_ADMIN_PASSWORD,
    }
}


# Internationalization
# https://docs.djangoproject.com/en/1.8/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.8/howto/static-files/

STATIC_URL = '/static/'


SUIT_CONFIG = {
    'ADMIN_NAME': 'LDAP Auth',
    'LIST_PER_PAGE': 50,
}

ACCOUNT_MIGRATION_APPS = [
    ("admin", "LogEntry", "user", "__first__"),
    ("auth_request", "ZoneUser", "user", "__first__"),
    ("auth_request", "ZoneGroup", "group", None),
]
