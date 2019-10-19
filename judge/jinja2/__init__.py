import itertools
import json

from django.utils.http import urlquote
from jinja2.ext import Extension
from mptt.utils import get_cached_trees
from statici18n.templatetags.statici18n import inlinei18n
from sass_processor.processor import sass_processor

from judge.highlight_code import highlight_code
from judge.user_translations import gettext
from . import (datetime, filesize, gravatar, language, markdown, rating, reference, render, social,
               spaceless, submission, timedelta)
from . import registry

registry.function('str', str)
registry.filter('str', str)
registry.filter('json', json.dumps)
registry.filter('highlight', highlight_code)
registry.filter('urlquote', urlquote)
registry.filter('roundfloat', round)
registry.function('inlinei18n', inlinei18n)
registry.function('mptt_tree', get_cached_trees)
registry.function('user_trans', gettext)
registry.function('sass_src', sass_processor)

@registry.function
def colnum(n):
    string = ''

    while n > 0:
        n, remainder = divmod(n - 1, 26)
        string = chr(65 + remainder) + string

    return string

@registry.function
def counter(start=1):
    return itertools.count(start).__next__


class DMOJExtension(Extension):
    def __init__(self, env):
        super(DMOJExtension, self).__init__(env)
        env.globals.update(registry.globals)
        env.filters.update(registry.filters)
        env.tests.update(registry.tests)
