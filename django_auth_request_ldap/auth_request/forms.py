from django import forms
from django.contrib.auth.forms import AuthenticationForm


class ZoneAuthenticationForm(AuthenticationForm):
    zone = forms.CharField(widget=forms.HiddenInput())
