from django.core.exceptions import ObjectDoesNotExist
from django.shortcuts import *

import json
from judge.models import Contest, Problem, Profile
from judge.templatetags.timedelta import nice_repr


def api_contest_list(request):
    js = {}
    for c in Contest.objects.filter(is_public=True):
        js[c.key] = {
            'name': c.name,
            'free_start': c.free_start,
            'start_time': c.start_time.isoformat() if c.start_time is not None else None,
            'time_limit': nice_repr(c.time_limit, 'concise'),
            'ongoing': c.ongoing
        }
    jso = json.dumps(js)
    return HttpResponse(jso, mimetype='application/json')


def api_problem_list(request):
    js = {}
    for p in Problem.objects.filter(is_public=True):
        js[p.code] = {
            'points': p.points,
            'partial': p.partial,
            'name': p.name,
            'group': p.group.full_name
        }
    jso = json.dumps(js)
    return HttpResponse(jso, mimetype='application/json')


def api_problem_info(request, problem):
    js = {}
    try:
        p = Problem.objects.get(code=problem)
        js = {
            'name': p.name,
            'authors': [a.user.username for a in p.authors.all()],
            'types': [t.full_name for t in p.types.all()],
            'group': p.group.full_name,
            'time_limit': p.time_limit,
            'memory_limit': p.memory_limit,
            'points': p.points,
            'partial': p.partial,
            'languages': list(p.allowed_languages.values_list('key', flat=True)),
        }
    except ObjectDoesNotExist:
        pass
    jso = json.dumps(js)
    return HttpResponse(jso, mimetype='application/json')


def api_user_list(request):
    js = {}
    for p in Profile.objects.all():
        js[p.user.username] = {
            'display_name': p.name,
            'points': p.points,
            'rank': p.display_rank
        }
    jso = json.dumps(js)
    return HttpResponse(jso, mimetype='application/json')


def api_user_info(request, user):
    js = {}
    try:
        p = Profile.objects.get(user_username=user)
        js = {
            'display_name': p.name,
            'points': p.points,
            'rank': p.display_rank,
            'solved_problems': [],  # TODO
        }
    except ObjectDoesNotExist:
        pass
    jso = json.dumps(js)
    return HttpResponse(jso, mimetype='a