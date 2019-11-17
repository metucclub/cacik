from django.core.management.base import BaseCommand
from django.contrib.auth.models import User, Group
from django.utils.text import slugify
from django.conf import settings

from judge.models import *

import os, sys, string
import json

slugs = []

def create_slug(x):
    slug = slugify(x)

    if slug == '':
        slug = 'team{}'.format(len(slugs))

    if slug in slugs:
        slug += str(slugs.count(slug))

    slugs.append(slug)

    return slug

class Command(BaseCommand):
    def handle(self, *args, **options):
        answer = input('delete non-staff users? [y/N]: ')

        if answer.lower() == 'y' or answer.lower() == 'yes':
            print('removing all non-staff users...')

            for u in User.objects.exclude(is_staff=True):
                u.delete()

        file_name = getattr(settings, 'TEAMS_JSON_FILE', os.path.join(settings.BASE_DIR, 'teams.json'))

        with open(file_name, 'r', encoding='utf-8') as f:
            teams = json.load(f)

            usernames = []
            participant_count = 0
            success = True

            for team in teams:
                username = team['email']
                passwd = team['passwd']

                if username in usernames:
                    success = False
                    print('error: duplicate email: "{}".'.format(username))

                    break
                else:
                    usernames.append(username)

                if 'group' in team:
                    if Group.objects.filter(name=team['group']).count() == 0:
                        success = False
                        print('error: group "{}" not found.'.format(team['group']))

                        break

            if success:
                default_lang = Language.objects.get(key='PY2')

                for team in teams:
                    username = team['email']
                    passwd = team['passwd']
                    team_name = team['name']
                    members = team['members']

                    participant_count += len(members)

                    new_user = User.objects.get_or_create(username=username,
                        defaults={
                            'email': username,
                            'is_active':True
                        })[0]
                    new_user.set_password(passwd)
                    new_user.save()

                    new_profile = Profile.objects.get_or_create(user=new_user)[0]
                    new_profile.display_name = '{} ({})'.format(
                        team_name, ', '.join(map(lambda u: u['last_name'], members)),
                    )
                    new_profile.notes = '\n'.join(
                        map(lambda u: '{} {}'.format(u['first_name'], u['last_name']), members),
                    )
                    new_profile.timezone = 'Europe/Istanbul'
                    new_profile.language = default_lang
                    new_profile.save()

                    if 'group' in team:
                        group_name = team['group']

                        group = Group.objects.filter(name=group_name).first()

                        if group:
                            group.user_set.add(new_user)

                print('successfully created {} teams with {} participants'.format(len(teams), participant_count))