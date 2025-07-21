from django.core.management.commands.runserver import Command as RunServerCommand
from django.core.management.base import BaseCommand


class Command(RunServerCommand):
    """
    Custom runserver command that skips migration checks.
    Used for local development when connecting to remote DB with limited permissions.
    """
    
    def check_migrations(self):
        """Override to skip migration checks completely."""
        pass
    
    def get_handler(self, *args, **options):
        """
        Returns the static files serving handler wrapping the default handler,
        if static files should be served. Otherwise returns the default handler.
        """
        handler = super().get_handler(*args, **options)
        return handler