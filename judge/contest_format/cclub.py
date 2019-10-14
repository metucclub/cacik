from datetime import timedelta
from django.core.exceptions import ValidationError
from django.db.models import Max
from django.template.defaultfilters import floatformat
from django.urls import reverse
from django.utils.functional import cached_property
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy

from judge.contest_format.base import BaseContestFormat
from judge.contest_format.registry import register_contest_format
from judge.utils.timedelta import nice_repr


@register_contest_format('cclub')
class CClubContestFormat(BaseContestFormat):
    name = gettext_lazy('CClub')
    config_defaults = {'penalty': 20}
    config_validators = {'penalty': lambda x: x >= 0}
    '''
        penalty: Number of penalty minutes each incorrect submission adds. Defaults to 20.
    '''

    @classmethod
    def validate(cls, config):
        if config is None:
            return

        if not isinstance(config, dict):
            raise ValidationError('CClub-styled contest expects no config or dict as config')

        for key, value in config.items():
            if key not in cls.config_defaults:
                raise ValidationError('unknown config key "%s"' % key)
            if not isinstance(value, type(cls.config_defaults[key])):
                raise ValidationError('invalid type for config key "%s"' % key)
            if not cls.config_validators[key](value):
                raise ValidationError('invalid value "%s" for config key "%s"' % (value, key))

    def __init__(self, contest, config):
        self.config = self.config_defaults.copy()
        self.config.update(config or {})
        self.contest = contest

    def update_participation(self, participation):
        cumtime = 0
        points = 0
        penalty = 0
        format_data = {}

        for result in participation.submissions.values('problem_id').annotate(
                time=Max('submission__date'), points=Max('points')
        ):
            wrong_submission_count = participation.submissions.filter(
                problem_id=result['problem_id'], submission__result__in=['WA', 'TLE', 'MLE', 'OLE', 'IR', 'RTE']
            ).count()

            dt = (result['time'] - participation.start).total_seconds()
            if result['points']:
                cumtime += dt
                cumtime += wrong_submission_count*self.config['penalty']*60
            format_data[str(result['problem_id'])] = {'time': dt, 'points': result['points'], 'penalty': wrong_submission_count}
            points += result['points']

        participation.cumtime = max(cumtime, 0)
        participation.score = points
        participation.format_data = format_data
        participation.save()

    def display_user_problem(self, participation, contest_problem):
        format_data = (participation.format_data or {}).get(str(contest_problem.id))
        if format_data:
            penalty = format_html('<small style="color:red"> ({penalty})</small>',
                                  penalty=floatformat(format_data['penalty'])) if format_data['penalty'] else ''
            return format_html(
                u'<td class="{state}">{points}{penalty}<div class="solving-time">{time}</div></td>',
                state=('pretest-' if self.contest.run_pretests_only and contest_problem.is_pretested else '') +
                      self.best_solution_state(format_data['points'], contest_problem.points),
                points=floatformat(format_data['points']),
                penalty=penalty,
                time=nice_repr(timedelta(seconds=format_data['time']), 'noday'),
            )
        else:
            return mark_safe('<td></td>')

    def display_participation_result(self, participation):
        return format_html(
            u'<td class="user-points">{points}<div class="solving-time">{cumtime}</div></td>',
            points=floatformat(participation.score),
            cumtime=nice_repr(timedelta(seconds=participation.cumtime), 'noday'),
        )

    def get_problem_breakdown(self, participation, contest_problems):
        return [(participation.format_data or {}).get(str(contest_problem.id)) for contest_problem in contest_problems]
