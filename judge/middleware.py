from django.conf import settings
from django.http import HttpResponseRedirect
from django.urls import Resolver404, resolve, reverse
from django.utils import timezone, translation
from django.utils.http import urlquote
from preferences import preferences

from judge.models import Contest, ContestParticipation

class ShortCircuitMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        try:
            callback, args, kwargs = resolve(request.path_info, getattr(request, 'urlconf', None))
        except Resolver404:
            callback, args, kwargs = None, None, None

        if getattr(callback, 'short_circuit_middleware', False):
            return callback(request, *args, **kwargs)
        return self.get_response(request)


class DMOJLoginMiddleware(object):
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        lang = request.COOKIES.get(settings.LANGUAGE_COOKIE_NAME)
        translation.activate(lang)

        if request.user.is_authenticated:
            profile = request.profile = request.user.profile
            login_2fa_path = reverse('login_2fa')
            if (profile.is_totp_enabled and not request.session.get('2fa_passed', False) and
                    request.path not in (login_2fa_path, reverse('auth_logout')) and
                    not request.path.startswith(settings.STATIC_URL)):
                return HttpResponseRedirect(login_2fa_path + '?next=' + urlquote(request.get_full_path()))
        else:
            request.profile = None
        return self.get_response(request)


class DMOJImpersonationMiddleware(object):
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_impersonate:
            request.profile = request.user.profile
        return self.get_response(request)


class ContestMiddleware(object):
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        profile = request.profile

        if profile:
            if not request.user.is_superuser and preferences.SitePreferences.active_contest and not preferences.SitePreferences.active_contest.ended:
                active_contest = preferences.SitePreferences.active_contest

                is_organizer = active_contest.organizers.filter(id=profile.id).exists()

                requires_access_code = (not is_organizer and active_contest.access_code)

                try:
                    participation = ContestParticipation.objects.get(
                        contest=active_contest, user=profile, virtual=(-1 if is_organizer else 0),
                    )
                except ContestParticipation.DoesNotExist:
                    if requires_access_code:
                        raise Exception()

                    participation = ContestParticipation.objects.create(
                        contest=active_contest, user=profile, virtual=(-1 if is_organizer else 0),
                        real_start=timezone.now(),
                    )

                profile.current_contest = participation
                profile.save()

                request.participation = participation
                request.in_contest = True

                active_contest._updating_stats_only = True
                active_contest.update_user_count()

            else:
                profile.update_contest()
                request.participation = profile.current_contest
                request.in_contest = request.participation is not None
        else:
            request.in_contest = False
            request.participation = None

        return self.get_response(request)
