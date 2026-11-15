"""Attempt delivery of queued task notifications."""

from django.core.management.base import BaseCommand

from notif.services import NotificationService


class Command(BaseCommand):
    help = "Deliver pending notifications and retain failures for a later retry."

    def handle(self, *args, **options):
        sent, failed = NotificationService.deliver_persisted()
        self.stdout.write(self.style.SUCCESS(f"Sent {sent}; failed {failed}."))
