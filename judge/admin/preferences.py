from django.contrib import admin

from preferences.admin import PreferencesAdmin

class SitePreferencesAdmin(PreferencesAdmin):
    readonly_fields = ('sites',)

    fieldsets = (
        (None, {'fields': ('site_name', 'site_admin_email', 'site_logo', 'active_contest')}),
        ('Futures', {'fields': ('use_display_name_as_public_name', 'enable_fts', 'enable_rss',
                'enable_filters')}),
        ('Accounts', {'fields': ('disable_registration', 'disable_mail_verification', 'disable_forgot_password',
                'disable_change_password')}),
        ('Comments', {'fields': ('no_comments',)}),
        ('Submissions', {'fields': ('hide_best_solutions',)}),
        ('Extras', {'fields': ('extra_css', 'extra_js', 'extra_body_end_html')}),
    )
