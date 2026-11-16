from .config import get_system_config


class DatabaseSessionTimeoutMiddleware:
    """Apply the current database setting to each authenticated session."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            request.session.set_expiry(get_system_config().session_timeout_seconds)
        return self.get_response(request)
