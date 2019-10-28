import logging
import re
from html.parser import HTMLParser
from urllib.parse import urlparse

import mistune
from django.conf import settings
from jinja2 import Markup
from lxml import html
from lxml.etree import ParserError, XMLSyntaxError

from judge.highlight_code import highlight_code
from judge.jinja2.markdown.lazy_load import lazy_load as lazy_load_processor
from judge.jinja2.markdown.math import MathInlineGrammar, MathInlineLexer, MathRenderer
from .. import registry

logger = logging.getLogger('judge.html')

NOFOLLOW_WHITELIST = getattr(settings, 'NOFOLLOW_EXCLUDED', set())


class CodeSafeInlineGrammar(mistune.InlineGrammar):
    double_emphasis = re.compile(r'^\*{2}([\s\S]+?)()\*{2}(?!\*)')  # **word**
    emphasis = re.compile(r'^\*((?:\*\*|[^\*])+?)()\*(?!\*)')  # *word*


class AwesomeInlineGrammar(MathInlineGrammar, CodeSafeInlineGrammar):
    pass


class AwesomeInlineLexer(MathInlineLexer, mistune.InlineLexer):
    grammar_class = AwesomeInlineGrammar


class AwesomeRenderer(MathRenderer, mistune.Renderer):
    def __init__(self, *args, **kwargs):
        self.nofollow = kwargs.pop('nofollow', True)
        self.parser = HTMLParser()
        super(AwesomeRenderer, self).__init__(*args, **kwargs)

    def _link_rel(self, href):
        if href:
            try:
                url = urlparse(href)
            except ValueError:
                return ' rel="nofollow"'
            else:
                if url.netloc and url.netloc not in NOFOLLOW_WHITELIST:
                    return ' rel="nofollow"'
        return ''

    def autolink(self, link, is_email=False):
        text = link = mistune.escape(link)
        if is_email:
            link = 'mailto:%s' % link
        return '<a href="%s"%s>%s</a>' % (link, self._link_rel(link), text)

    def table(self, header, body):
        return (
            '<table class="table">\n<thead>%s</thead>\n'
            '<tbody>\n%s</tbody>\n</table>\n'
        ) % (header, body)

    def link(self, link, title, text):
        link = mistune.escape_link(link)
        if not title:
            return '<a href="%s"%s>%s</a>' % (link, self._link_rel(link), text)
        title = mistune.escape(title, quote=True)
        return '<a href="%s" title="%s"%s>%s</a>' % (link, title, self._link_rel(link), text)

    def block_code(self, code, lang=None):
        if not lang:
            return '\n<pre><code>%s</code></pre>\n' % mistune.escape(code).rstrip()
        return highlight_code(code, lang)

    def header(self, text, level, *args, **kwargs):
        return super(AwesomeRenderer, self).header(text, level + 2, *args, **kwargs)


@registry.filter
def markdown(value, style, math_engine=None, lazy_load=False):
    styles = getattr(settings, 'MARKDOWN_STYLES', {}).get(style, getattr(settings, 'MARKDOWN_DEFAULT_STYLE', {}))
    escape = styles.get('safe_mode', True)
    nofollow = styles.get('nofollow', True)

    post_processors = []
    if lazy_load:
        post_processors.append(lazy_load_processor)

    renderer = AwesomeRenderer(escape=escape, nofollow=nofollow, math_engine=math_engine)
    markdown = mistune.Markdown(renderer=renderer, inline=AwesomeInlineLexer,
                                parse_block_html=1, parse_inline_html=1)
    result = markdown(value)

    if post_processors:
        try:
            tree = html.fromstring(result, parser=html.HTMLParser(recover=True))
        except (XMLSyntaxError, ParserError) as e:
            if result and (not isinstance(e, ParserError) or e.args[0] != 'Document is empty'):
                logger.exception('Failed to parse HTML string')
            tree = html.Element('div')
        for processor in post_processors:
            processor(tree)
        result = html.tostring(tree, encoding='unicode')
    return Markup(result)
