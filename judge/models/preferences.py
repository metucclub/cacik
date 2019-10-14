from django.db import models

from preferences.models import Preferences

class SitePreferences(Preferences):
    site_name = models.CharField(max_length=100, blank=True, null=True)
    site_admin_email = models.CharField(max_length=100, blank=True, null=True)

    site_logo = models.ImageField(blank=True, null=True)

    enable_fts = models.BooleanField(default=False)

    extended_problems_page = models.BooleanField(default=False)