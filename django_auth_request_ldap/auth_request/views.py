
from django.conf import settings
from django.core.urlresolvers import reverse
# Avoid shadowing the login() and logout() views below.
from django.contrib.auth import REDIRECT_FIELD_NAME, login as auth_login
from django.http import HttpResponseRedirect, HttpResponse
from django.shortcuts import resolve_url
from django.template.response import TemplateResponse
from django.utils.http import is_safe_url
from django.utils.six.moves.urllib.parse import urlencode
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.debug import sensitive_post_parameters

from .models import Zone
from .forms import ZoneAuthenticationForm

from .enums import ACTION_ACCESS, ACTION_DENIED, ACTION_LOGIN, ACTION_DISABLED, ACTION_UNKNOWN, ACCESS_DISPLAY


def get_response(request, response_type=HttpResponse, *args, **kwargs):
    user = request.user
    resp = response_type(*args, **kwargs)
    if user.is_authenticated():
        resp['X-Zone-Username'] = getattr(user, user.USERNAME_FIELD)
        resp['X-Zone-Email'] = user.email
        resp['X-Zone-Userid'] = user.pk
        resp['X-Zone-First-Name'] = user.first_name
        resp['X-Zone-Last-Name'] = user.last_name
    else:
        resp['X-Zone-Username'] = ""
        resp['X-Zone-Email'] = ""
        resp['X-Zone-Userid'] = 0
        resp['X-Zone-First-Name'] = ""
        resp['X-Zone-First-Name'] = ""
    resp['X-Zone-SID'] = request.session.session_key
    return resp


def check_auth(request, zone_name=None):
    redirect_to = request.META.get('HTTP_X_ORIGINAL_URI', '')
    if not zone_name:
        zone_name = request.META.get('HTTP_X_ZONE_NAME', 'default')

    access, cached = Zone.process_request(request.user, zone_name)

    if access == ACTION_ACCESS:
        resp = get_response(request)
        resp.status_code = 200
    elif access == ACTION_LOGIN:
        url_parts = urlencode({
            REDIRECT_FIELD_NAME: redirect_to,
        })
        resp = get_response(request, HttpResponseRedirect, "%s?%s" % (reverse('auth_request:login'), url_parts))
    elif access in (ACTION_DENIED, ACTION_DISABLED, ACTION_UNKNOWN):
        resp = get_response(request)
        resp.status_code = 403
    return resp


def check_auth_info(request, zone_name=None, template_name="auth_request/info.html"):
    if not request.user.is_superuser or request.GET.get('apply'):
        return check_auth(request, zone_name)

    redirect_to = request.META.get('HTTP_X_ORIGINAL_URI', '')
    if not zone_name:
        zone_name = request.META.get('HTTP_X_ZONE_NAME', 'default')

    access, cached = Zone.process_request(request.user, zone_name)

    try:
        zone = Zone.objects.get(code=zone_name)
        grouprules = list(zone.groups.all().prefetch_related('group'))
        userrules = list(zone.users.all().prefetch_related('user'))
    except Zone.DoesNotExist:
        zone = None
        grouprules = []
        userrules = []

    context = {
        'access': access,
        'access_display': ACCESS_DISPLAY[access],
        'cached': cached,
        'zone_name': zone_name,
        'zone': zone,
        'redirect_to': redirect_to,

        'grouprules': grouprules,
        'userrules': userrules,
    }

    return TemplateResponse(request, template_name, context)


@sensitive_post_parameters()
@csrf_protect
@never_cache
def login(request, zone=None, template_name="auth_request/login.html",
          redirect_field_name=REDIRECT_FIELD_NAME,
          authentication_form=ZoneAuthenticationForm,
          current_app=None, extra_context=None):
    """
    Displays the login form and handles the login action.
    """
    redirect_to = request.POST.get(redirect_field_name,
                                   request.GET.get(redirect_field_name, ''))

    if request.method == "POST":
        form = authentication_form(request, data=request.POST)
        if form.is_valid():

            # Ensure the user-originating redirection url is safe.
            if not is_safe_url(url=redirect_to, host=request.get_host()):
                redirect_to = resolve_url(settings.LOGIN_REDIRECT_URL)

            # Okay, security check complete. Log the user in.
            auth_login(request, form.get_user())
            return HttpResponseRedirect(redirect_to)
    else:
        form = authentication_form(request)

    context = {
        'form': form,
        redirect_field_name: redirect_to,
    }
    if extra_context is not None:
        context.update(extra_context)

    if current_app is not None:
        request.current_app = current_app

    return TemplateResponse(request, template_name, context)
