import logging

from django.conf import settings
from django.core.mail import send_mail


logger = logging.getLogger(__name__)


class NotificationService:
    @staticmethod
    def enqueue(recipient, subject, message):
        try:
            return send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[recipient],
                fail_silently=False,
            )
        except Exception:
            logger.exception("Unable to send notification email.")
            return 0
