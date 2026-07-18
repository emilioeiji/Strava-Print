"""Delete expired projects that are not attached to commercial orders."""

from __future__ import annotations

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from studio.models import PrintProject
from studio.services import delete_project_files


class Command(BaseCommand):
    help = "Remove projetos antigos sem pedidos para aplicar a política de retenção."

    def add_arguments(self, parser) -> None:
        parser.add_argument("--days", type=int, default=90)
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options) -> None:
        cutoff = timezone.now() - timedelta(days=max(options["days"], 1))
        projects = PrintProject.objects.filter(updated_at__lt=cutoff, orders__isnull=True).distinct()
        count = projects.count()
        if options["dry_run"]:
            self.stdout.write(f"{count} projeto(s) seriam removidos.")
            return
        for project in projects.iterator():
            delete_project_files(project)
            project.delete()
        self.stdout.write(self.style.SUCCESS(f"{count} projeto(s) removidos."))
