import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dmoj.settings')

try:
    import MySQLdb  # noqa: F401, imported for side effect
except ImportError:
    pass

from django.core.wsgi import get_wsgi_application  # noqa: E402, django must be imported here
application = get_wsgi_application()
