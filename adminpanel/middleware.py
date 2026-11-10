from .models import SystemConfig


class DatabaseSessionTimeoutMiddleware:
    """Apply the current database setting to each authenticated session."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            config = SystemConfig.objects.first()
            if config:
                request.session.set_expiry(config.session_timeout_seconds)
        return self.get_response(request)
