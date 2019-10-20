from collections import defaultdict
from operator import itemgetter

import pytz
from django.utils.translation import gettext_lazy as _


def make_timezones():
    data = defaultdict(list)
    for tz in pytz.all_timezones:
        if '/' in tz:
            area, loc = tz.split('/', 1)
        else:
            area, loc = 'Other', tz
        if not loc.startswith('GMT'):
            data[area].append((tz, loc))
    return sorted(data.items(), key=itemgetter(0))


TIMEZONE = make_timezones()
del make_timezones

MATH_ENGINES_CHOICES = (
    ('svg', _('SVG with PNG fallback')),
    ('jax', _('MathJax with SVG/PNG fallback')),
    ('auto', _('Detect best quality')),
)

EFFECTIVE_MATH_ENGINES = ('svg', 'jax')
