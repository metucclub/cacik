import os
import shutil
import sys

from django.conf import settings
from django.core.management.base import BaseCommand
from django.template.loader import get_template
from django.utils import translation

from judge.models import Problem, ProblemTranslation
from judge.pdf_problems import DefaultPdfMaker, PhantomJSPdfMaker


class Command(BaseCommand):
    help = 'renders a PDF file of a problem'

    def add_arguments(self, parser):
        parser.add_argument('code', help='code of problem to render')
        parser.add_argument('directory', nargs='?', help='directory to store temporaries')
        parser.add_argument('-l', '--language', default=settings.LANGUAGE_CODE,
                            help='language to render PDF in')

    def handle(self, *args, **options):
        try:
            problem = Problem.objects.get(code=options['code'])
        except Problem.DoesNotExist:
            print('Bad problem code')
            return

        try:
            trans = problem.translations.get(language=options['language'])
        except ProblemTranslation.DoesNotExist:
            trans = None

        directory = options['directory']
        with options['engine'](directory, clean_up=directory is None) as maker, \
                translation.override(options['language']):
            problem_name = problem.name if trans is None else trans.name
            maker.html = get_template('problem/raw.html').render({
                'problem': problem,
                'problem_name': problem_name,
                'description': problem.description if trans is None else trans.description,
                'url': '',
            }).replace('"//', '"https://').replace("'//", "'https://")
            maker.title = problem_name

            maker.load(file, os.path.join(settings.STATIC_ROOT, 'css', 'style.css'))
            maker.load(file, os.path.join(settings.STATIC_ROOT, 'css', 'pygment-github.css'))
            maker.load(file, os.path.join(settings.STATIC_ROOT, 'js', 'mathjax_config.js'))

            maker.make(debug=True)
            if not maker.success:
                print(maker.log, file=sys.stderr)
            elif directory is None:
                shutil.move(maker.pdffile, problem.code + '.pdf')
