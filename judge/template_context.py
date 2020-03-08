from functools import partial

from django.conf import settings
from django.contrib.auth.context_processors import PermWrapper
from django.contrib.sites.shortcuts import get_current_site
from django.core.cache import cache
from django.utils.functional import SimpleLazyObject, new_method_proxy

from judge import event_poster as event

from .models import NavigationBar, Profile

class FixedSimpleLazyObject(SimpleLazyObject):
    if not hasattr(SimpleLazyObject, '__iter__'):
        __iter__ = new_method_proxy(iter)


def get_resource(request):
    use_https = getattr(settings, 'DMOJ_SSL', 0)
    if use_https == 1:
        scheme = 'https' if request.is_secure() else 'http'
    elif use_https > 1:
        scheme = 'https'
    else:
        scheme = 'http'
    return {
        'PYGMENT_THEME': getattr(settings, 'PYGMENT_THEME', 'pygment-github.css'),
        'DMOJ_SCHEME': scheme,
        'DMOJ_CANONICAL': getattr(settings, 'DMOJ_CANONICAL', ''),
    }


def get_profile(request):
    if request.user.is_authenticated:
        return Profile.objects.get_or_create(user=request.user)[0]
    return None


def comet_location(request):
    if getattr(settings, 'EVENT_DAEMON_FORCE_SSL', False) or request.is_secure():
        websocket = getattr(settings, 'EVENT_DAEMON_GET_SSL', settings.EVENT_DAEMON_GET)
        poll = getattr(settings, 'EVENT_DAEMON_POLL_SSL', settings.EVENT_DAEMON_POLL)
    else:
        websocket = settings.EVENT_DAEMON_GET
        poll = settings.EVENT_DAEMON_POLL
    return {'EVENT_DAEMON_LOCATION': websocket,
            'EVENT_DAEMON_POLL_LOCATION': poll}


def __nav_tab(path):
    result = list(NavigationBar.objects.extra(where=['%s REGEXP BINARY regex'], params=[path])[:1])
    return result[0].get_ancestors(include_self=True).values_list('key', flat=True) if result else []


def general_info(request):
    path = request.get_full_path()
    return {
        'nav_tab': FixedSimpleLazyObject(partial(__nav_tab, request.path)),
        'nav_bar': NavigationBar.objects.all(),
        'LOGIN_RETURN_PATH': '' if path.startswith('/accounts/') else path,
        'perms': PermWrapper(request.user),
    }


def site(request):
    return {'site': get_current_site(request)}

def event_config(request):
    return {'last_msg': event.last()}

