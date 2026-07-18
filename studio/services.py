"""Application services for rendering, storage, jobs, pricing and fulfillment."""

from __future__ import annotations

import logging
import tempfile
import zipfile
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import asdict
from datetime import timedelta
from io import BytesIO
from pathlib import Path

from django.conf import settings
from django.core.files import File
from django.core.files.base import ContentFile
from django.core.mail import send_mail
from django.db import connection, transaction
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify

from strava_print.domain.models import Model3DSettings, PhotoSettings, Project
from strava_print.export.package import export_all
from strava_print.gpx.parser import parse_gpx
from strava_print.layouts.templates import load_template
from strava_print.layouts.themes import MATERIALS, ROUTE_COLORS, THEMES
from strava_print.renderers.preview_renderer import render_mounted_preview
from studio.models import ExportArtifact, ExportJob, Order, PrintProject

logger = logging.getLogger(__name__)


def _copy_field(field, target: Path) -> Path | None:
    if not field:
        return None
    target.parent.mkdir(parents=True, exist_ok=True)
    with field.open("rb") as source, target.open("wb") as destination:
        while chunk := source.read(1024 * 1024):
            destination.write(chunk)
    return target


@contextmanager
def materialized_sources(project: PrintProject) -> Iterator[tuple[Path, Path | None, Path | None]]:
    """Materialize protected local or cloud-backed uploads for the rendering engine."""
    with tempfile.TemporaryDirectory(prefix="gpx-print-sources-") as directory:
        root = Path(directory)
        gpx = _copy_field(project.gpx_file, root / project.source_filename)
        if gpx is None:
            raise ValueError("O projeto não possui um arquivo GPX.")
        photo = _copy_field(project.photo_file, root / Path(project.photo_file.name).name) if project.photo_file else None
        dem = _copy_field(project.dem_file, root / Path(project.dem_file.name).name) if project.dem_file else None
        yield gpx, photo, dem


def update_activity_metadata(project: PrintProject) -> None:
    with materialized_sources(project) as (gpx_path, _, _):
        activity = parse_gpx(gpx_path)
    project.metrics_data = asdict(activity.metrics)
    if project.name == "Nova atividade":
        project.name = Path(project.gpx_file.name).stem.replace("_", " ")
    if project.title == "Morning Ride" and project.name:
        project.title = project.name
    project.status = PrintProject.Status.READY
    project.error_message = ""
    project.save(update_fields=["metrics_data", "name", "title", "status", "error_message", "updated_at"])


def build_domain_project(
    project: PrintProject, photo_path: Path | None = None, dem_path: Path | None = None
) -> Project:
    theme_name = project.theme_name if project.theme_name in THEMES else "Gallery Edition"
    material_name = project.theme_settings.get("material_name", next(iter(MATERIALS)))
    route_color_name = project.theme_settings.get("route_color_name", next(iter(ROUTE_COLORS)))
    theme = {
        **THEMES[theme_name],
        "material": MATERIALS.get(material_name, next(iter(MATERIALS.values()))),
        "accent": ROUTE_COLORS.get(route_color_name, next(iter(ROUTE_COLORS.values()))),
    }
    photo_data = {**project.photo_settings, "path": str(photo_path) if photo_path else None}
    model_data = {
        "mode": "terrain" if dem_path else "flat_map",
        **project.model3d_settings,
        "dem_path": str(dem_path) if dem_path else None,
    }
    return Project(
        source_gpx=project.source_filename,
        template=project.template_name,
        title=project.title,
        subtitle=project.subtitle,
        date=project.date,
        location=project.location,
        country=project.country,
        description=project.description,
        activity_type=project.activity_type,
        units=project.units,
        metrics=project.visible_metrics,
        theme=theme,
        photo=PhotoSettings(**photo_data),
        route_2d=project.route_settings,
        model_3d=Model3DSettings(**model_data),
    )


def generate_preview(project: PrintProject) -> str:
    with materialized_sources(project) as (gpx_path, photo_path, dem_path):
        activity = parse_gpx(gpx_path)
        domain_project = build_domain_project(project, photo_path, dem_path)
        template = load_template(domain_project.template)
        image = render_mounted_preview(activity, domain_project, template, dpi=120)
    buffer = BytesIO()
    image.save(buffer, format="JPEG", quality=90, optimize=True)
    if project.preview_file:
        project.preview_file.delete(save=False)
    project.preview_file.save("mounted-preview.jpg", ContentFile(buffer.getvalue()), save=False)
    project.metrics_data = asdict(activity.metrics)
    project.status = PrintProject.Status.READY
    project.error_message = ""
    project.save()
    return reverse("studio:preview-image", args=[project.id])


def generate_exports(project: PrintProject) -> list[ExportArtifact]:
    with materialized_sources(project) as (gpx_path, photo_path, dem_path):
        activity = parse_gpx(gpx_path)
        domain_project = build_domain_project(project, photo_path, dem_path)
        with tempfile.TemporaryDirectory(prefix="gpx-print-export-") as directory:
            output = Path(directory)
            stem = slugify(project.name) or "activity"
            files = export_all(activity, domain_project, output, stem)
            package_path = output / f"{stem}_complete.zip"
            with zipfile.ZipFile(package_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                for path in files.values():
                    archive.write(path, path.name)
            files["package"] = package_path

            artifacts = []
            for kind, path in files.items():
                artifact, _ = ExportArtifact.objects.get_or_create(project=project, kind=kind)
                if artifact.file:
                    artifact.file.delete(save=False)
                with path.open("rb") as source:
                    artifact.file.save(path.name, File(source), save=False)
                artifact.size_bytes = path.stat().st_size
                artifact.save()
                artifacts.append(artifact)
    project.status = PrintProject.Status.COMPLETE
    project.error_message = ""
    project.save(update_fields=["status", "error_message", "updated_at"])
    return artifacts


def delete_project_files(project: PrintProject) -> None:
    for field in (project.gpx_file, project.photo_file, project.dem_file, project.preview_file):
        if field:
            field.delete(save=False)
    for artifact in project.artifacts.all():
        if artifact.file:
            artifact.file.delete(save=False)


def enqueue_export(project: PrintProject, user, session_key: str) -> ExportJob:
    active = project.export_jobs.filter(
        status__in=[ExportJob.Status.QUEUED, ExportJob.Status.RUNNING]
    ).first()
    if active:
        return active
    job = ExportJob.objects.create(
        project=project,
        requested_by=user if getattr(user, "is_authenticated", False) else None,
        session_key=session_key,
    )
    if settings.EXPORT_JOBS_INLINE:
        process_export_job(job)
        job.refresh_from_db()
    return job


def process_export_job(job: ExportJob) -> ExportJob:
    if job.status == ExportJob.Status.COMPLETE:
        return job
    job.status = ExportJob.Status.RUNNING
    job.progress = 10
    job.attempts += 1
    job.started_at = timezone.now()
    job.error_message = ""
    job.save()
    try:
        generate_preview(job.project)
        job.progress = 35
        job.save(update_fields=["progress"])
        generate_exports(job.project)
    except (OSError, RuntimeError, ValueError) as error:
        logger.exception("Export job %s failed", job.id)
        job.status = ExportJob.Status.FAILED
        job.error_message = str(error)
        job.finished_at = timezone.now()
        job.project.status = PrintProject.Status.ERROR
        job.project.error_message = str(error)
        job.project.save(update_fields=["status", "error_message", "updated_at"])
    else:
        job.status = ExportJob.Status.COMPLETE
        job.progress = 100
        job.finished_at = timezone.now()
    job.save()
    return job


@transaction.atomic
def claim_next_export_job() -> ExportJob | None:
    stale_before = timezone.now() - timedelta(minutes=settings.EXPORT_JOB_STALE_MINUTES)
    stale = ExportJob.objects.filter(
        status=ExportJob.Status.RUNNING,
        started_at__lt=stale_before,
    )
    stale.filter(attempts__lt=settings.EXPORT_JOB_MAX_ATTEMPTS).update(
        status=ExportJob.Status.QUEUED,
        error_message="Job recuperado após interrupção do worker.",
    )
    stale.filter(attempts__gte=settings.EXPORT_JOB_MAX_ATTEMPTS).update(
        status=ExportJob.Status.FAILED,
        finished_at=timezone.now(),
        error_message="Número máximo de tentativas excedido.",
    )
    jobs = ExportJob.objects.filter(status=ExportJob.Status.QUEUED).order_by("created_at")
    if connection.features.has_select_for_update_skip_locked:
        jobs = jobs.select_for_update(skip_locked=True)
    elif connection.features.has_select_for_update:
        jobs = jobs.select_for_update()
    job = jobs.first()
    if job:
        job.status = ExportJob.Status.RUNNING
        job.started_at = timezone.now()
        job.save(update_fields=["status", "started_at"])
    return job


def calculate_order(order: Order) -> None:
    unit_price = settings.PRODUCT_PRICES[order.product]
    order.currency = settings.STORE_CURRENCY
    order.subtotal_amount = unit_price * order.quantity
    order.shipping_amount = settings.PRODUCT_SHIPPING[order.product]
    order.total_amount = order.subtotal_amount + order.shipping_amount


def format_money(amount: int, currency: str = "jpy") -> str:
    if currency.lower() == "jpy":
        return f"¥{amount:,.0f}"
    return f"{currency.upper()} {amount / 100:,.2f}"


def send_order_email(order: Order, template: str, subject: str) -> None:
    context = {"order": order, "total": format_money(order.total_amount, order.currency)}
    body = render_to_string(template, context)
    recipients = [order.customer_email]
    if settings.STORE_CONTACT_EMAIL and settings.STORE_CONTACT_EMAIL not in recipients:
        recipients.append(settings.STORE_CONTACT_EMAIL)
    send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, recipients, fail_silently=True)


def confirm_order_paid(order: Order, payment_reference: str) -> bool:
    """Idempotently mark an order paid and trigger production once."""
    with transaction.atomic():
        locked = Order.objects.select_for_update().get(id=order.id)
        if locked.paid_at or locked.status == Order.Status.CANCELLED:
            return False
        locked.status = Order.Status.PAID
        locked.payment_reference = payment_reference
        locked.paid_at = timezone.now()
        locked.save(update_fields=["status", "payment_reference", "paid_at", "updated_at"])
    send_order_email(locked, "studio/emails/order_paid.txt", f"Pagamento confirmado · {locked.reference}")
    return True


def metric_cards(project: PrintProject) -> list[dict[str, str]]:
    values = project.metrics_data
    distance_m = float(values.get("distance_m") or 0)
    moving_s = values.get("moving_time_s") or values.get("duration_s")
    gain = values.get("elevation_gain_m")
    speed = values.get("average_speed_mps")

    def duration(value: float | None) -> str:
        if value is None:
            return "—"
        total = int(value)
        hours, remainder = divmod(total, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours}:{minutes:02d}:{seconds:02d}" if hours else f"{minutes}:{seconds:02d}"

    return [
        {"label": "Distância", "value": f"{distance_m / 1000:.2f}", "unit": "km"},
        {"label": "Tempo", "value": duration(moving_s), "unit": "h:min:s"},
        {"label": "Elevação", "value": f"{float(gain or 0):.0f}", "unit": "m"},
        {"label": "Média", "value": f"{float(speed or 0) * 3.6:.1f}", "unit": "km/h"},
    ]
