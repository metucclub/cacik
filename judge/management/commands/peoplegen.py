from django.core.management.base import BaseCommand
from django.contrib.auth.models import User, Group
from django.utils.text import slugify
from django.conf import settings

from judge.models import *

import os, sys, string
import json

ERROR_TEXT = '\033[1m\033[91merror:\033[0m'

slugs = []

def create_slug(x):
    global slugs

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
            emails = []
            participant_count = 0
            success = True

            for team in teams:
                username = create_slug(team['name'])
                email = team['email']
                password = team['password']

                if username in usernames:
                    success = False
                    print('{} duplicate username: "{}".'.format(ERROR_TEXT, username))

                    break
                else:
                    usernames.append(username)
                    team['username'] = username

                if email in emails:
                    success = False
                    print('{} duplicate email: "{}".'.format(ERROR_TEXT, email))

                    break
                else:
                    emails.append(email)

                if 'group' in team:
                    if Group.objects.filter(name=team['group']).count() == 0:
                        success = False
                        print('{} group "{}" not found.'.format(ERROR_TEXT, team['group']))

                        break

            if success:
                default_lang = Language.objects.get(key='PY3')

                for team in teams:
                    username = team['username']
                    email = team['email']
                    password = team['password']
                    team_name = team['name']
                    members = team['members']

                    participant_count += len(members)

                    new_user = User.objects.get_or_create(username=username, email=email,
                        defaults={
                            'is_active': True,
                        })[0]
                    new_user.set_password(password)
                    new_user.save()

                    new_profile = Profile.objects.get_or_create(user=new_user)[0]
                    new_profile.display_name = '{} ({})'.format(
                        team_name, ', '.join(map(lambda u: str(u['last_name']).title(), members)),
                    )
                    new_profile.notes = '\n'.join(
                        map(lambda u: '{} {}'.format(str(u['first_name']).title(), str(u['last_name']).title()), members),
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
