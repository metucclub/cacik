from django.utils.timezone import now

from judge.models import Profile


class LogUserAccessMiddleware(object):
    def __init__(self, get_response=None):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        if (hasattr(request, 'user') and request.user.is_authenticated and
                not getattr(request, 'no_profile_update', False)):
            updates = {'last_access': now()}
            # Decided on using REMOTE_ADDR as nginx will translate it to the external IP that hits it.
            # No, REMOTE_ADDR not working on proxies, use HTTP_X_REAL_IP
            if request.META.get('HTTP_X_REAL_IP'):
                updates['ip'] = request.META.get('HTTP_X_REAL_IP')
            elif request.META.get('REMOTE_ADDR'):
                updates['ip'] = request.META.get('REMOTE_ADDR')
            Profile.objects.filter(user_id=request.user.pk).update(**updates)

        return response
