"""Process queued exports without requiring Redis or a separate queue service."""

from __future__ import annotations

import time

from django.conf import settings
from django.core.management.base import BaseCommand

from studio.services import claim_next_export_job, process_export_job


class Command(BaseCommand):
    help = "Processa a fila de exportações do GPX Print Studio."

    def add_arguments(self, parser) -> None:
        parser.add_argument("--once", action="store_true", help="Processa no máximo um job e encerra.")

    def handle(self, *args, **options) -> None:
        self.stdout.write("Worker de exportação iniciado.")
        while True:
            job = claim_next_export_job()
            if job:
                self.stdout.write(f"Processando {job.id} · {job.project.name}")
                process_export_job(job)
                self.stdout.write(f"Resultado: {job.get_status_display()}")
            if options["once"]:
                return
            if not job:
                time.sleep(settings.EXPORT_WORKER_POLL_SECONDS)
