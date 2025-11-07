from django.core.management.base import BaseCommand

from admin_panel.models import Status


class Command(BaseCommand):
    help = "Adds default data to the database"

    def handle(self, *args, **options):
        transaction_statuses = [
            ("1", "created", "створений"),
            ("2", "skipped", "пропущено"),
            ("3", "in_progress", "в процесі"),
            ("4", "failed", "не вдалося"),
            ("5", "completed", "успіх"),
        ]
        for record_id, status_code, status_title in transaction_statuses:
            Status.objects.get_or_create(
                record_id=record_id, status_code=status_code, status_title=status_title
            )

        print("Initial data added successfully!")
