from operator import attrgetter

import pyotp
from django import forms
from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db.models import Q
from django.forms import CharField, Form, ModelForm
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _

from django_ace import AceWidget
from judge.models import Contest, Language, PrivateMessage, Problem, Profile, Submission
from judge.utils.subscription import newsletter_id
from judge.widgets import HeavyPreviewPageDownWidget, MathJaxPagedownWidget, PagedownWidget, Select2MultipleWidget, \
    Select2Widget


def fix_unicode(string, unsafe=tuple('\u202a\u202b\u202d\u202e')):
    return string + (sum(k in unsafe for k in string) - string.count('\u202c')) * '\u202c'


class ProfileForm(ModelForm):
    if newsletter_id is not None:
        newsletter = forms.BooleanField(label=_('Subscribe to contest updates'), initial=False, required=False)
    test_site = forms.BooleanField(label=_('Enable experimental features'), initial=False, required=False)

    class Meta:
        model = Profile
        fields = ['about', 'timezone', 'language']
        widgets = {
            'timezone': Select2Widget(attrs={'style': 'width:200px'}),
            'language': Select2Widget(attrs={'style': 'width:200px'}),
        }

        if HeavyPreviewPageDownWidget is not None:
            widgets['about'] = HeavyPreviewPageDownWidget(
                preview=reverse_lazy('profile_preview'),
                attrs={'style': 'max-width:700px;min-width:700px;width:700px'},
            )

    def clean(self):
        return self.cleaned_data

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super(ProfileForm, self).__init__(*args, **kwargs)


class ProblemSubmitForm(ModelForm):
    source = CharField(max_length=65536, widget=AceWidget(theme=getattr(settings, 'ACE_THEME', 'chrome'), no_ace_media=True))

    def __init__(self, *args, **kwargs):
        super(ProblemSubmitForm, self).__init__(*args, **kwargs)
        self.fields['problem'].empty_label = None
        self.fields['problem'].widget = forms.HiddenInput()
        self.fields['language'].empty_label = None
        self.fields['language'].label_from_instance = attrgetter('display_name')
        self.fields['language'].queryset = Language.objects.filter(judges__online=True).distinct()

    class Meta:
        model = Submission
        fields = ['problem', 'language']

class NewMessageForm(ModelForm):
    class Meta:
        model = PrivateMessage
        fields = ['title', 'content']
        widgets = {}
        if PagedownWidget is not None:
            widgets['content'] = MathJaxPagedownWidget()

class CustomAuthenticationForm(forms.Form):
    email = forms.CharField(widget=forms.TextInput(attrs={'autofocus': True, 'placeholder': _('Email or Username')}))
    password = forms.CharField(
        label=_("Password"),
        strip=False,
        widget=forms.PasswordInput(attrs={'autocomplete': 'current-password', 'placeholder': _('Password')}),
    )

    def __init__(self, request=None, *args, **kwargs):
        self.request = request
        self.user_cache = None
        super().__init__(*args, **kwargs)

        self.has_google_auth = self._has_social_auth('GOOGLE_OAUTH2')
        self.has_facebook_auth = self._has_social_auth('FACEBOOK')
        self.has_github_auth = self._has_social_auth('GITHUB_SECURE')

    def _has_social_auth(self, key):
        return (getattr(settings, 'SOCIAL_AUTH_%s_KEY' % key, None) and
                getattr(settings, 'SOCIAL_AUTH_%s_SECRET' % key, None))

    def clean(self):
        email = self.cleaned_data.get('email')
        password = self.cleaned_data.get('password')

        try:
            user = User.objects.get(email=email)
        except:
            try:
                user = User.objects.get(username=email)
            except:
                raise self.get_invalid_login_error()

        username = user.username

        if username is not None and password:
            self.user_cache = authenticate(self.request, username=username, password=password)

            if self.user_cache is None:
                raise self.get_invalid_login_error()
            else:
                if not self.user_cache.is_active:
                    raise forms.ValidationError(
                        _("This account is inactive."),
                        code='inactive',
                    )

        return self.cleaned_data

    def get_user(self):
        return self.user_cache

    def get_invalid_login_error(self):
        return forms.ValidationError(
            _(
                "Please enter a correct email and password. Note that both "
                "fields may be case-sensitive."
            ),
            code='invalid_login',
        )

class NoAutoCompleteCharField(forms.CharField):
    def widget_attrs(self, widget):
        attrs = super(NoAutoCompleteCharField, self).widget_attrs(widget)
        attrs['autocomplete'] = 'off'
        return attrs


class TOTPForm(Form):
    TOLERANCE = getattr(settings, 'DMOJ_TOTP_TOLERANCE_HALF_MINUTES', 1)

    totp_token = NoAutoCompleteCharField(validators=[
        RegexValidator('^[0-9]{6}$', _('Two Factor Authentication tokens must be 6 decimal digits.')),
    ])

    def __init__(self, *args, **kwargs):
        self.totp_key = kwargs.pop('totp_key')
        super(TOTPForm, self).__init__(*args, **kwargs)

    def clean_totp_token(self):
        if not pyotp.TOTP(self.totp_key).verify(self.cleaned_data['totp_token'], valid_window=self.TOLERANCE):
            raise ValidationError(_('Invalid Two Factor Authentication token.'))


class ProblemCloneForm(Form):
    code = CharField(max_length=20, validators=[RegexValidator('^[a-z0-9]+$', _('Problem code must be ^[a-z0-9]+$'))])

    def clean_code(self):
        code = self.cleaned_data['code']
        if Problem.objects.filter(code=code).exists():
            raise ValidationError(_('Problem with code already exists.'))
        return code


class ContestCloneForm(Form):
    key = CharField(max_length=20, validators=[RegexValidator('^[a-z0-9]+$', _('Contest id must be ^[a-z0-9]+$'))])

    def clean_key(self):
        key = self.cleaned_data['key']
        if Contest.objects.filter(key=key).exists():
            raise ValidationError(_('Contest with key already exists.'))
        return key

class ContestShareMessageForm(Form):
    message = CharField(widget=forms.Textarea(attrs={"rows":4, "cols":27}), max_length=1000)
