from django.conf import settings

__all__ = ['last', 'post']

if not getattr(settings, 'EVENT_DAEMON_USE', False):
    real = False

    def post(channel, message):
        return 0

    def last():
        return 0
else:
    from .event_poster_ws import last, post
    real = True
