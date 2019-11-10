try:
    import MySQLdb  # noqa: F401, imported for side effect
except ImportError:
    pass

# noinspection PyUnresolvedReferences
from dmoj.celery import app  # noqa: F401, imported for side effect
