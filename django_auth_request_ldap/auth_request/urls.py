from django.conf.urls import include, url
from .views import login, check_auth

urlpatterns = [
    url(r'^$',          check_auth, name='auth_check'),
    url(r'^login/$',    login, name='login'),
]
