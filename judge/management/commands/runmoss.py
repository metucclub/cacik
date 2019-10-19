from django.conf import settings
from django.core.management.base import BaseCommand
from moss import *

from judge.models import Contest, ContestParticipation, Submission


class Command(BaseCommand):
    help = 'Checks for duplicate code using MOSS'

    LANG_MAPPING = {
        ('C', MOSS_LANG_C),
        ('C++', MOSS_LANG_CC),
        ('Java', MOSS_LANG_JAVA),
        ('Lisp', MOSS_LANG_LISP),
        ('Haskell', MOSS_LANG_HASKELL),
        ('Fortran', MOSS_LANG_FORTRAN),
        ('Perl', MOSS_LANG_PERL),
        ('Python', MOSS_LANG_PYTHON),
        ('Pypy', MOSS_LANG_PYTHON),
        ('Prolog', MOSS_LANG_PROLOG),
        ('VB', MOSS_LANG_VB),
        ('CSHARP', MOSS_LANG_CSHARP),
        ('JavaScript', MOSS_LANG_JAVASCRIPT),
        ('Verilog', MOSS_LANG_VERILOG),
    }

    def add_arguments(self, parser):
        parser.add_argument('contest', help='the id of the contest')

    def handle(self, *args, **options):
        moss_api_key = settings.MOSS_API_KEY
        if moss_api_key is None:
            print('No MOSS API Key supplied')
            return
        contest = options['contest']

        for problem in Contest.objects.get(key=contest).problems.order_by('code'):
            print('========== %s / %s ==========' % (problem.code, problem.name))
            for dmoj_lang, moss_lang in self.LANG_MAPPING:
                print("%s: " % dmoj_lang, end=' ')
                subs = Submission.objects.filter(
                    contest__participation__virtual__in=(ContestParticipation.LIVE, ContestParticipation.SPECTATE),
                    contest__participation__contest__key=contest,
                    result='AC', problem__id=problem.id,
                    language__common_name=dmoj_lang,
                ).values_list('user__user__username', 'source__source')
                if not subs:
                    print('<no submissions>')
                    continue

                moss_call = MOSS(moss_api_key, language=moss_lang, matching_file_limit=100,
                                 comment='%s - %s' % (contest, problem.code))

                users = set()

                for username, source in subs:
                    if username in users:
                        continue
                    users.add(username)
                    moss_call.add_file_from_memory(username, source.encode('utf-8'))

                print('(%d): %s' % (subs.count(), moss_call.process()))
