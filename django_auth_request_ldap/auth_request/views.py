
from django.conf import settings
from django.core.urlresolvers import reverse
# Avoid shadowing the login() and logout() views below.
from django.contrib.auth import (
    REDIRECT_FIELD_NAME, get_user_model, login as auth_login,
    logout as auth_logout, update_session_auth_hash,
)
from django.http import HttpResponseRedirect, HttpResponse
from django.shortcuts import resolve_url
from django.template.response import TemplateResponse
from django.utils.http import is_safe_url
from django.utils.six.moves.urllib.parse import urlencode
from django.utils.translation import ugettext as _
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.debug import sensitive_post_parameters

from .models import Zone, ZONE_ACCESS_ALLOWED
from .forms import ZoneAuthenticationForm


def check_auth(request):
    redirect_to = request.META.get('HTTP_X_ORIGINAL_URI', '')
    zone_name = request.META.get('HTTP_X_ZONE_NAME', 'default')

    user = request.user

    if user.is_authenticated():
        print(zone_name)
        action, access = Zone.process_access_request(zone_name, user)
        if access == ZONE_ACCESS_ALLOWED:
            resp = HttpResponse()
            resp.status_code = 200
            resp['X-Zone-Username'] = getattr(user, user.USERNAME_FIELD)
            resp['X-Zone-Email'] = user.email
            return resp

    url_parts = urlencode({
        REDIRECT_FIELD_NAME: redirect_to,
        'zone': zone_name,
    })
    return HttpResponseRedirect("%s?%s" % (reverse('auth_request:login'), url_parts))


@sensitive_post_parameters()
@csrf_protect
@never_cache
def login(request, template_name="auth_request/login.html",
          redirect_field_name=REDIRECT_FIELD_NAME,
          authentication_form=ZoneAuthenticationForm,
          current_app=None, extra_context=None):
    """
    Displays the login form and handles the login action.
    """
    redirect_to = request.POST.get(redirect_field_name,
                                   request.GET.get(redirect_field_name, ''))
    zone_name = request.POST.get('zone', request.GET.get('zone', ''))

    if request.method == "POST":
        form = authentication_form(request, data=request.POST)
        if form.is_valid():

            # Ensure the user-originating redirection url is safe.
            if not is_safe_url(url=redirect_to, host=request.get_host()):
                redirect_to = resolve_url(settings.LOGIN_REDIRECT_URL)

            # Okay, security check complete. Log the user in.
            user = form.get_user()
            print("Is Valid")
            if Zone.process_login(zone_name, user):
                print("Allowed zone")
                auth_login(request, user)
                return HttpResponseRedirect(redirect_to)
    else:
        form = authentication_form(request)
    print("Login required")

    context = {
        'form': form,
        'zone': zone_name,
        redirect_field_name: redirect_to,
    }
    if extra_context is not None:
        context.update(extra_context)

    if current_app is not None:
        request.current_app = current_app

    return TemplateResponse(request, template_name, context)
