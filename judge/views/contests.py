from calendar import Calendar, SUNDAY
from collections import defaultdict, namedtuple
from datetime import date, datetime, time, timedelta
from functools import partial
from itertools import chain
from operator import attrgetter

from django import forms
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.core.cache import cache
from django.core.exceptions import ImproperlyConfigured, ObjectDoesNotExist
from django.db import IntegrityError
from django.db.models import Case, IntegerField, Max, Min, Q, Sum, When
from django.http import Http404, HttpResponse, HttpResponseBadRequest, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.template.defaultfilters import date as date_filter
from django.urls import reverse
from django.utils import timezone
from django.utils.functional import cached_property
from django.utils.html import escape, format_html
from django.utils.timezone import make_aware
from django.utils.translation import gettext as _, gettext_lazy
from django.views.generic import ListView, TemplateView
from django.views.generic.detail import BaseDetailView, DetailView

from preferences import preferences

from judge import event_poster as event
from judge.comments import CommentedDetailView
from judge.forms import ContestCloneForm, ContestShareMessageForm
from judge.models import Contest, ContestParticipation, ContestProblem, ContestTag, Problem, ProblemClarification, Profile, Ticket
from judge.utils.opengraph import generate_opengraph
from judge.utils.ranker import ranker
from judge.utils.views import DiggPaginatorMixin, SingleObjectFormView, TitleMixin, generic_message
from judge.utils.problems import contest_completed_ids

__all__ = ['ContestList', 'ContestDetail', 'ContestRanking', 'ContestJoin', 'ContestLeave', 'ContestCalendar',
           'ContestClone', 'contest_ranking_ajax', 'ContestParticipationList', 'get_contest_ranking_list',
           'base_contest_ranking_list']


def _find_contest(request, key, private_check=True):
    try:
        contest = Contest.objects.get(key=key)
        if private_check and not contest.is_accessible_by(request.user):
            raise ObjectDoesNotExist()
    except ObjectDoesNotExist:
        return generic_message(request, _('No such contest'),
                               _('Could not find a contest with the key "%s".') % key, status=404), False
    return contest, True


class ContestListMixin(object):
    def get_queryset(self):
        queryset = Contest.objects.all()
        if not self.request.user.has_perm('judge.see_private_contest'):
            q = Q(is_visible=True)
            if self.request.user.is_authenticated:
                q |= Q(organizers=self.request.profile)
            queryset = queryset.filter(q)
        if not self.request.user.has_perm('judge.edit_all_contest'):
            q = Q(is_private=False)
            if self.request.user.is_authenticated:
                q |= Q(is_private=True, private_contestants=self.request.profile)
            queryset = queryset.filter(q)
        return queryset.distinct()


class ContestList(DiggPaginatorMixin, TitleMixin, ContestListMixin, ListView):
    model = Contest
    paginate_by = 20
    template_name = 'contest/list.html'
    title = gettext_lazy('Contests')
    context_object_name = 'past_contests'

    @cached_property
    def _now(self):
        return timezone.now()

    def _get_queryset(self):
        return super(ContestList, self).get_queryset() \
            .order_by('-start_time', 'key').prefetch_related('tags', 'organizers')

    def get_queryset(self):
        return self._get_queryset().filter(end_time__lt=self._now)

    def get_context_data(self, **kwargs):
        context = super(ContestList, self).get_context_data(**kwargs)
        present, active, future = [], [], []
        for contest in self._get_queryset().exclude(end_time__lt=self._now):
            if contest.start_time > self._now:
                future.append(contest)
            else:
                present.append(contest)

        if self.request.user.is_authenticated:
            for participation in ContestParticipation.objects.filter(virtual=0, user=self.request.profile,
                                                                     contest_id__in=present) \
                    .select_related('contest').prefetch_related('contest__organizers'):
                if not participation.ended:
                    active.append(participation)
                    present.remove(participation.contest)

        active.sort(key=attrgetter('end_time'))
        future.sort(key=attrgetter('start_time'))
        context['active_participations'] = active
        context['current_contests'] = present
        context['future_contests'] = future
        context['now'] = self._now
        context['first_page_href'] = '.'
        return context

    def get(self, request, *args, **kwargs):
        if preferences.SitePreferences.active_contest:
            raise Http404()

        return super(ContestList, self).get(request, *args, **kwargs)


class PrivateContestError(Exception):
    def __init__(self, name, private_users, orgs):
        self.name = name
        self.private_users = private_users
        self.orgs = orgs


class ContestMixin(object):
    context_object_name = 'contest'
    model = Contest
    slug_field = 'key'
    slug_url_kwarg = 'contest'

    @cached_property
    def is_organizer(self):
        return self.check_organizer()

    def check_organizer(self, contest=None, profile=None):
        if profile is None:
            if not self.request.user.is_authenticated:
                return False
            profile = self.request.profile
        return (contest or self.object).organizers.filter(id=profile.id).exists()

    def get_context_data(self, **kwargs):
        context = super(ContestMixin, self).get_context_data(**kwargs)
        if self.request.user.is_authenticated:
            profile = self.request.profile
            in_contest = context['in_contest'] = (profile.current_contest is not None and
                                                  profile.current_contest.contest == self.object)
            if in_contest:
                context['participation'] = profile.current_contest
                context['participating'] = True
            else:
                try:
                    context['participation'] = profile.contest_history.get(contest=self.object, virtual=0)
                except ContestParticipation.DoesNotExist:
                    context['participating'] = False
                    context['participation'] = None
                else:
                    context['participating'] = True
        else:
            context['participating'] = False
            context['participation'] = None
            context['in_contest'] = False
        context['now'] = timezone.now()
        context['is_organizer'] = self.is_organizer

        if not self.object.og_image or not self.object.summary:
            metadata = generate_opengraph('generated-meta-contest:%d' % self.object.id,
                                          self.object.description, 'contest')
        context['meta_description'] = self.object.summary or metadata[0]
        context['og_image'] = self.object.og_image or metadata[1]

        return context

    def get_object(self, queryset=None):
        contest = super(ContestMixin, self).get_object(queryset)
        user = self.request.user
        profile = self.request.profile

        if (profile is not None and
                ContestParticipation.objects.filter(id=profile.current_contest_id, contest_id=contest.id).exists()):
            return contest

        if not contest.is_visible and not user.has_perm('judge.see_private_contest') and (
                not user.has_perm('judge.edit_own_contest') or
                not self.check_organizer(contest, profile)):
            raise Http404()

        if contest.is_private:
            private_contest_error = PrivateContestError(contest.name, contest.private_contestants.all())

            if profile is None:
                raise private_contest_error
            if user.has_perm('judge.edit_all_contest'):
                return contest
            if not (contest.is_private and contest.private_contestants.filter(id=profile.id).exists()):
                raise private_contest_error

        return contest

    def dispatch(self, request, *args, **kwargs):
        try:
            return super(ContestMixin, self).dispatch(request, *args, **kwargs)
        except Http404:
            key = kwargs.get(self.slug_url_kwarg, None)
            if key:
                return generic_message(request, _('No such contest'),
                                       _('Could not find a contest with the key "%s".') % key)
            else:
                return generic_message(request, _('No such contest'),
                                       _('Could not find such contest.'))
        except PrivateContestError as e:
            return render(request, 'contest/private.html', {
                'orgs': e.orgs, 'title': _('Access to contest "%s" denied') % escape(e.name),
            }, status=403)

class ContestDetail(ContestMixin, TitleMixin, CommentedDetailView):
    template_name = 'contest/contest.html'

    def get_comment_page(self):
        return 'c:%s' % self.object.key

    def get_title(self):
        return self.object.name

    def get_context_data(self, **kwargs):
        context = super(ContestDetail, self).get_context_data(**kwargs)

        clarifications = ProblemClarification.objects.filter(problem__in=self.object.problems.all())
        context['has_clarifications'] = clarifications.count() > 0
        context['clarifications'] = clarifications.order_by('-date')

        if self.request.user.is_authenticated:
            if self.request.in_contest:
                context['completed_problem_ids'] = contest_completed_ids(self.request.profile.current_contest)

            context['own_open_tickets'] = (Ticket.objects.filter(user=self.request.profile, is_open=True).order_by('-id')
                                           .prefetch_related('linked_item').select_related('user__user'))

        context['contest_problems'] = Problem.objects.filter(contests__contest=self.object) \
            .order_by('contests__order').defer('description') \
            .annotate(has_public_editorial=Sum(Case(When(solution__is_public=True, then=1),
                                                    default=0, output_field=IntegerField()))) \
            .add_i18n_name(self.request.LANGUAGE_CODE)
        return context


class ContestClone(ContestMixin, PermissionRequiredMixin, TitleMixin, SingleObjectFormView):
    title = _('Clone Contest')
    template_name = 'contest/clone.html'
    form_class = ContestCloneForm
    permission_required = 'judge.clone_contest'

    def form_valid(self, form):
        contest = self.object

        tags = contest.tags.all()
        private_contestants = contest.private_contestants.all()
        contest_problems = contest.contest_problems.all()

        contest.pk = None
        contest.is_visible = False
        contest.user_count = 0
        contest.key = form.cleaned_data['key']
        contest.save()

        contest.tags.set(tags)
        contest.private_contestants.set(private_contestants)
        contest.organizers.add(self.request.profile)

        for problem in contest_problems:
            problem.contest = contest
            problem.pk = None
        ContestProblem.objects.bulk_create(contest_problems)

        return HttpResponseRedirect(reverse('admin:judge_contest_change', args=(contest.id,)))

class ContestShareMessage(ContestMixin, PermissionRequiredMixin, TitleMixin, SingleObjectFormView):
    title = _('Share Contest Wide Message')
    template_name = 'contest/message.html'
    form_class = ContestShareMessageForm
    permission_required = 'judge.share_contest_message'

    def form_valid(self, form):
        contest = self.object

        message = form.cleaned_data['message']

        event.post('contest-message-{}'.format(contest.key), {
            'type': 'contest-message',
            'message': message,
        })

        return HttpResponseRedirect(reverse('contest_view', args=(contest.key,)))


class ContestAccessDenied(Exception):
    pass


class ContestAccessCodeForm(forms.Form):
    access_code = forms.CharField(max_length=255)

    def __init__(self, *args, **kwargs):
        super(ContestAccessCodeForm, self).__init__(*args, **kwargs)
        self.fields['access_code'].widget.attrs.update({'autocomplete': 'off'})


class ContestJoin(LoginRequiredMixin, ContestMixin, BaseDetailView):
    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        return self.ask_for_access_code()

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        try:
            return self.join_contest(request)
        except ContestAccessDenied:
            if request.POST.get('access_code'):
                return self.ask_for_access_code(ContestAccessCodeForm(request.POST))
            else:
                return HttpResponseRedirect(request.path)

    def join_contest(self, request, access_code=None):
        contest = self.object

        if not contest.can_join and not self.is_organizer:
            return generic_message(request, _('Contest not ongoing'),
                                   _('"%s" is not currently ongoing.') % contest.name)

        profile = request.profile
        if profile.current_contest is not None:
            return generic_message(request, _('Already in contest'),
                                   _('You are already in a contest: "%s".') % profile.current_contest.contest.name)

        if not request.user.is_superuser and contest.banned_users.filter(id=profile.id).exists():
            return generic_message(request, _('Banned from joining'),
                                   _('You have been declared persona non grata for this contest. '
                                     'You are permanently barred from joining this contest.'))

        requires_access_code = (not (request.user.is_superuser or self.is_organizer) and
                                contest.access_code and access_code != contest.access_code)
        if contest.ended:
            if requires_access_code:
                raise ContestAccessDenied()

            while True:
                virtual_id = (ContestParticipation.objects.filter(contest=contest, user=profile)
                              .aggregate(virtual_id=Max('virtual'))['virtual_id'] or 0) + 1
                try:
                    participation = ContestParticipation.objects.create(
                        contest=contest, user=profile, virtual=virtual_id,
                        real_start=timezone.now(),
                    )
                # There is obviously a race condition here, so we keep trying until we win the race.
                except IntegrityError:
                    pass
                else:
                    break
        else:
            try:
                participation = ContestParticipation.objects.get(
                    contest=contest, user=profile, virtual=(-1 if self.is_organizer else 0),
                )
            except ContestParticipation.DoesNotExist:
                if requires_access_code:
                    raise ContestAccessDenied()

                participation = ContestParticipation.objects.create(
                    contest=contest, user=profile, virtual=(-1 if self.is_organizer else 0),
                    real_start=timezone.now(),
                )
            else:
                if participation.ended:
                    participation = ContestParticipation.objects.get_or_create(
                        contest=contest, user=profile, virtual=-1,
                        defaults={'real_start': timezone.now()},
                    )[0]

        profile.current_contest = participation
        profile.save()
        contest._updating_stats_only = True
        contest.update_user_count()

        return HttpResponseRedirect(reverse('contest_view', args=(contest.key,)))

    def ask_for_access_code(self, form=None):
        contest = self.object
        wrong_code = False
        if form:
            if form.is_valid():
                if form.cleaned_data['access_code'] == contest.access_code:
                    return self.join_contest(self.request, form.cleaned_data['access_code'])
                wrong_code = True
        else:
            form = ContestAccessCodeForm()
        return render(self.request, 'contest/access_code.html', {
            'form': form, 'wrong_code': wrong_code,
            'title': _('Enter access code for "%s"') % contest.name,
        })


class ContestLeave(LoginRequiredMixin, ContestMixin, BaseDetailView):
    def post(self, request, *args, **kwargs):
        contest = self.get_object()

        profile = request.profile
        if profile.current_contest is None or profile.current_contest.contest_id != contest.id:
            return generic_message(request, _('No such contest'),
                                   _('You are not in contest "%s".') % contest.key, 404)

        profile.remove_contest()
        return HttpResponseRedirect(reverse('contest_view', args=(contest.key,)))


ContestDay = namedtuple('ContestDay', 'date weekday is_pad is_today starts ends oneday')


class ContestCalendar(TitleMixin, ContestListMixin, TemplateView):
    firstweekday = SUNDAY
    weekday_classes = ['sun', 'mon', 'tue', 'wed', 'thu', 'fri', 'sat']
    template_name = 'contest/calendar.html'

    def get(self, request, *args, **kwargs):
        if preferences.SitePreferences.active_contest:
            raise Http404()

        try:
            self.year = int(kwargs['year'])
            self.month = int(kwargs['month'])
        except (KeyError, ValueError):
            raise ImproperlyConfigured(_('ContestCalendar requires integer year and month'))
        self.today = timezone.now().date()
        return self.render()

    def render(self):
        context = self.get_context_data()
        return self.render_to_response(context)

    def get_contest_data(self, start, end):
        end += timedelta(days=1)
        contests = self.get_queryset().filter(Q(start_time__gte=start, start_time__lt=end) |
                                              Q(end_time__gte=start, end_time__lt=end)).defer('description')
        starts, ends, oneday = (defaultdict(list) for i in range(3))
        for contest in contests:
            start_date = timezone.localtime(contest.start_time).date()
            end_date = timezone.localtime(contest.end_time - timedelta(seconds=1)).date()
            if start_date == end_date:
                oneday[start_date].append(contest)
            else:
                starts[start_date].append(contest)
                ends[end_date].append(contest)
        return starts, ends, oneday

    def get_table(self):
        calendar = Calendar(self.firstweekday).monthdatescalendar(self.year, self.month)
        starts, ends, oneday = self.get_contest_data(make_aware(datetime.combine(calendar[0][0], time.min)),
                                                     make_aware(datetime.combine(calendar[-1][-1], time.min)))
        return [[ContestDay(
            date=date, weekday=self.weekday_classes[weekday], is_pad=date.month != self.month,
            is_today=date == self.today, starts=starts[date], ends=ends[date], oneday=oneday[date],
        ) for weekday, date in enumerate(week)] for week in calendar]

    def get_context_data(self, **kwargs):
        context = super(ContestCalendar, self).get_context_data(**kwargs)

        try:
            month = date(self.year, self.month, 1)
        except ValueError:
            raise Http404()
        else:
            context['title'] = _('Contests in %(month)s') % {'month': date_filter(month, _("F Y"))}

        dates = Contest.objects.aggregate(min=Min('start_time'), max=Max('end_time'))
        min_month = (self.today.year, self.today.month)
        if dates['min'] is not None:
            min_month = dates['min'].year, dates['min'].month
        max_month = (self.today.year, self.today.month)
        if dates['max'] is not None:
            max_month = max((dates['max'].year, dates['max'].month), (self.today.year, self.today.month))

        month = (self.year, self.month)
        if month < min_month or month > max_month:
            # 404 is valid because it merely declares the lack of existence, without any reason
            raise Http404()

        context['now'] = timezone.now()
        context['calendar'] = self.get_table()
        context['curr_month'] = date(self.year, self.month, 1)

        if month > min_month:
            context['prev_month'] = date(self.year - (self.month == 1), 12 if self.month == 1 else self.month - 1, 1)
        else:
            context['prev_month'] = None

        if month < max_month:
            context['next_month'] = date(self.year + (self.month == 12), 1 if self.month == 12 else self.month + 1, 1)
        else:
            context['next_month'] = None
        return context


class CachedContestCalendar(ContestCalendar):
    def render(self):
        key = 'contest_cal:%d:%d' % (self.year, self.month)
        cached = cache.get(key)
        if cached is not None:
            return HttpResponse(cached)
        response = super(CachedContestCalendar, self).render()
        response.render()
        cached.set(key, response.content)
        return response


ContestRankingProfile = namedtuple(
    'ContestRankingProfile',
    'id user css_class username points cumtime participation '
    'participation_rating problem_cells result_cell',
)

BestSolutionData = namedtuple('BestSolutionData', 'code points time state is_pretested')


def make_contest_ranking_profile(contest, is_scoreboard_frozen, participation, contest_problems):
    user = participation.user

    return ContestRankingProfile(
        id=user.id,
        user=user.user,
        css_class=user.css_class,
        username=user.username,
        points=participation.frozen_score if is_scoreboard_frozen else participation.score,
        cumtime=participation.frozen_cumtime if is_scoreboard_frozen else participation.cumtime,
        participation_rating=participation.rating.rating if hasattr(participation, 'rating') else None,
        problem_cells=[contest.format.display_user_problem(is_scoreboard_frozen, participation, contest_problem)
                    for contest_problem in contest_problems],
        result_cell=contest.format.display_participation_result(is_scoreboard_frozen, participation),
        participation=participation,
    )


def base_contest_ranking_list(contest, is_scoreboard_frozen, problems, queryset):
    return [make_contest_ranking_profile(contest, is_scoreboard_frozen, participation, problems)
        for participation in queryset.select_related('user__user', 'rating').defer('user__about')]


def contest_ranking_list(contest, is_scoreboard_frozen, problems):
    if is_scoreboard_frozen:
        return base_contest_ranking_list(contest, is_scoreboard_frozen, problems, contest.users.filter(virtual=0, user__is_unlisted=False)
                                     .order_by('-frozen_score', 'frozen_cumtime'))


    return base_contest_ranking_list(contest, is_scoreboard_frozen, problems, contest.users.filter(virtual=0, user__is_unlisted=False)
                                     .order_by('-score', 'cumtime'))


def get_contest_ranking_list(request, contest, participation=None, ranking_list=contest_ranking_list,
                             show_current_virtual=True, ranker=ranker):
    problems = list(contest.contest_problems.select_related('problem').defer('problem__description').order_by('order'))

    is_scoreboard_frozen = not contest.can_see_real_scoreboard(request.user)

    if contest.hide_scoreboard and contest.is_in_contest(request.user):
        return ([(_('???'), make_contest_ranking_profile(contest, is_scoreboard_frozen, request.profile.current_contest, problems))],
                problems)

    users = ranker(ranking_list(contest, is_scoreboard_frozen, problems), key=attrgetter('points', 'cumtime'))

    if show_current_virtual:
        if participation is None and request.user.is_authenticated:
            participation = request.profile.current_contest
            if participation is None or participation.contest_id != contest.id:
                participation = None
        if participation is not None and participation.virtual:
            users = chain([('-', make_contest_ranking_profile(contest, is_scoreboard_frozen, participation, problems))], users)
    return users, problems


def contest_ranking_ajax(request, contest, participation=None):
    contest, exists = _find_contest(request, contest)
    if not exists:
        return HttpResponseBadRequest('Invalid contest', content_type='text/plain')

    if not contest.can_see_scoreboard(request.user):
        raise Http404()

    users, problems = get_contest_ranking_list(request, contest, participation)
    return render(request, 'contest/ranking-table.html', {
        'users': users,
        'problems': problems,
        'contest': contest,
        'has_rating': contest.ratings.exists(),
    })


class ContestRankingBase(ContestMixin, TitleMixin, DetailView):
    template_name = 'contest/ranking.html'
    tab = None

    def get_title(self):
        raise NotImplementedError()

    def get_content_title(self):
        return self.object.name

    def get_ranking_list(self):
        raise NotImplementedError()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        if not self.object.can_see_scoreboard(self.request.user):
            raise Http404()

        users, problems = self.get_ranking_list()
        context['users'] = users
        context['problems'] = problems
        context['tab'] = self.tab
        return context


class ContestRanking(ContestRankingBase):
    tab = 'ranking'

    def get_title(self):
        return _('%s Scoreboard') % self.object.name

    def get_ranking_list(self):
        return get_contest_ranking_list(self.request, self.object)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['has_rating'] = self.object.ratings.exists()

        if self.request.user.is_authenticated and self.request.in_contest:
            context['completed_problem_ids'] = contest_completed_ids(self.request.profile.current_contest)

        return context


class ContestParticipationList(LoginRequiredMixin, ContestRankingBase):
    tab = 'participation'

    def get_title(self):
        if self.profile == self.request.profile:
            return _('Your participation in %s') % self.object.name
        return _("%s's participation in %s") % (self.profile.username, self.object.name)

    def get_ranking_list(self):
        queryset = self.object.users.filter(user=self.profile, virtual__gte=0).order_by('-virtual')
        live_link = format_html('<a href="{2}#!{1}">{0}</a>', _('Live'), self.profile.username,
                                reverse('contest_ranking', args=[self.object.key]))

        return get_contest_ranking_list(
            self.request, self.object, show_current_virtual=False,
            ranking_list=partial(base_contest_ranking_list, queryset=queryset),
            ranker=lambda users, key: ((user.participation.virtual or live_link, user) for user in users))

    def get_context_data(self, **kwargs):
        if self.object.hide_participation_tab:
            raise Http404()

        context = super().get_context_data(**kwargs)
        context['has_rating'] = False
        context['now'] = timezone.now()
        context['rank_header'] = _('Participation')
        return context

    def get(self, request, *args, **kwargs):
        if 'user' in kwargs:
            self.profile = get_object_or_404(Profile, user__username=kwargs['user'])
        else:
            self.profile = self.request.profile
        return super().get(request, *args, **kwargs)


class ContestTagDetailAjax(DetailView):
    model = ContestTag
    slug_field = slug_url_kwarg = 'name'
    context_object_name = 'tag'
    template_name = 'contest/tag-ajax.html'


class ContestTagDetail(TitleMixin, ContestTagDetailAjax):
    template_name = 'contest/tag.html'

    def get_title(self):
        return _('Contest tag: %s') % self.object.name
