from django.db import models

from preferences.models import Preferences

from judge.models.contest import Contest

class SitePreferences(Preferences):
    site_name = models.CharField(max_length=100, blank=True, null=True)
    site_admin_email = models.CharField(max_length=100, blank=True, null=True)

    site_logo = models.ImageField(blank=True, null=True)

    active_contest = models.ForeignKey(Contest, on_delete=models.SET_NULL, blank=True, null=True)

    enable_fts = models.BooleanField(default=False)

    no_comments = models.BooleanField(default=False)
    enable_filters = models.BooleanField(default=False)
    hide_best_solutions = models.BooleanField(default=False)