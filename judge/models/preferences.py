from django.db import models

from preferences.models import Preferences

class SitePreferences(Preferences):
    site_name = models.CharField(max_length=100, blank=True, null=True)
    site_admin_email = models.CharField(max_length=100, blank=True, null=True)

    site_logo = models.ImageField(blank=True, null=True)