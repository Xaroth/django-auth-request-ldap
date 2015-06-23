from django.conf.urls import include, url
from .views import check_auth, check_auth_info
from django.contrib.auth.views import login

urlpatterns = [
    url(r'^$',                          check_auth, name='auth-check'),
    url(r'^info/$',                     check_auth_info, name='auth-info'),
    url(r'^info/(?P<zone_name>[-\w]+)/$', check_auth_info, name='named-auth-info'),
    url(r'^login/$',                    login, {'template_name': "auth_request/login.html"}, name='login'),
]
