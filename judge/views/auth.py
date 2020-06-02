from django.contrib.auth import views as auth_views
from django.http import Http404
from django.utils.translation import ugettext_lazy as _

from preferences import preferences

from judge.forms import CustomAuthenticationForm

class LoginView(auth_views.LoginView):
    template_name = 'registration/login.html'
    extra_context = {'title': _('Login')}
    authentication_form = CustomAuthenticationForm
    redirect_authenticated_user = True


class UserLogoutView(auth_views.LogoutView):
    next_page = 'home'


class PasswordChangeView(auth_views.PasswordChangeView):
    template_name='registration/password_change_form.html'

    def get_context_data(self, **kwargs):
        if preferences.SitePreferences.disable_change_password:
            raise Http404()

        return super(PasswordChangeView, self).get_context_data(**kwargs)

class PasswordChangeDoneView(auth_views.PasswordChangeDoneView):
    template_name='registration/password_change_done.html'

    def get_context_data(self, **kwargs):
        if preferences.SitePreferences.disable_change_password:
            raise Http404()

        return super(PasswordChangeDoneView, self).get_context_data(**kwargs)


class PasswordResetView(auth_views.PasswordResetView):
    template_name='registration/password_reset.html'
    html_email_template_name='registration/password_reset_email.html'
    email_template_name='registration/password_reset_email.txt'

    def get_context_data(self, **kwargs):
        if preferences.SitePreferences.disable_forgot_password:
            raise Http404()

        return super(PasswordResetView, self).get_context_data(**kwargs)


class PasswordResetConfirmView(auth_views.PasswordResetConfirmView):
    template_name='registration/password_reset_confirm.html',
    def get_context_data(self, **kwargs):
        if preferences.SitePreferences.disable_forgot_password:
            raise Http404()

        return super(PasswordResetConfirmView, self).get_context_data(**kwargs)


class PasswordResetCompleteView(auth_views.PasswordResetCompleteView):
    template_name='registration/password_reset_complete.html',

    def get_context_data(self, **kwargs):
        if preferences.SitePreferences.disable_forgot_password:
            raise Http404()

        return super(PasswordResetCompleteView, self).get_context_data(**kwargs)


class PasswordResetDoneView(auth_views.PasswordResetDoneView):
    template_name='registration/password_reset_done.html',

    def get_context_data(self, **kwargs):
        if preferences.SitePreferences.disable_forgot_password:
            raise Http404()

        return super(PasswordResetDoneView, self).get_context_data(**kwargs)
