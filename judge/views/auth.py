from django.contrib.auth import views
from django.http import Http404
from django.utils.translation import ugettext_lazy as _

from preferences import preferences

from judge.forms import CustomAuthenticationForm

class LoginView(views.LoginView):
    template_name = 'registration/login.html'
    extra_context = {'title': _('Login')}
    authentication_form = CustomAuthenticationForm
    redirect_authenticated_user = True


class UserLogoutView(views.LogoutView):
    next_page = 'home'


class PasswordChangeView(views.PasswordChangeView):
    template_name='registration/password_change_form.html'

    def get_context_data(self, **kwargs):
        if preferences.SitePreferences.disable_change_password:
            raise Http404()

        return super(views.PasswordChangeView).get_context_data(**kwargs)


class PasswordChangeDoneView(views.PasswordChangeDoneView):
    template_name='registration/password_change_done.html'

    def get_context_data(self, **kwargs):
        if preferences.SitePreferences.disable_change_password:
            raise Http404()

        return super(views.PasswordChangeView).get_context_data(**kwargs)



class PasswordResetView(views.PasswordResetView):
    template_name='registration/password_reset.html'
    html_email_template_name='registration/password_reset_email.html'
    email_template_name='registration/password_reset_email.txt'

    def get_context_data(self, **kwargs):
        if preferences.SitePreferences.disable_forgot_password:
            raise Http404()

        return super(views.PasswordChangeView).get_context_data(**kwargs)



class PasswordResetConfirmView(views.PasswordResetConfirmView):
    template_name='registration/password_reset_confirm.html',
    def get_context_data(self, **kwargs):
        if preferences.SitePreferences.disable_forgot_password:
            raise Http404()

        return super(views.PasswordChangeView).get_context_data(**kwargs)



class PasswordResetCompleteView(views.PasswordResetCompleteView):
    template_name='registration/password_reset_complete.html',

    def get_context_data(self, **kwargs):
        if preferences.SitePreferences.disable_forgot_password:
            raise Http404()

        return super(views.PasswordChangeView).get_context_data(**kwargs)



class PasswordResetDoneView(views.PasswordResetDoneView):
    template_name='registration/password_reset_done.html',

    def get_context_data(self, **kwargs):
        if preferences.SitePreferences.disable_forgot_password:
            raise Http404()

        return super(views.PasswordChangeView).get_context_data(**kwargs)



