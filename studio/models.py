"""Persistent projects and generated assets."""

from __future__ import annotations

import uuid
from pathlib import Path

from django.conf import settings
from django.db import models


def project_upload_path(instance: PrintProject, filename: str) -> str:
    return f"projects/{instance.id}/sources/{Path(filename).name}"


def preview_upload_path(instance: PrintProject, filename: str) -> str:
    return f"projects/{instance.id}/previews/{Path(filename).name}"


def artifact_upload_path(instance: ExportArtifact, filename: str) -> str:
    return f"projects/{instance.project_id}/exports/{Path(filename).name}"


class PrintProject(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Rascunho"
        READY = "ready", "Pronto"
        PROCESSING = "processing", "Gerando"
        COMPLETE = "complete", "Concluído"
        ERROR = "error", "Erro"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="print_projects",
        null=True,
        blank=True,
    )
    session_key = models.CharField(max_length=40, blank=True, db_index=True)
    name = models.CharField(max_length=120, default="Nova atividade")
    title = models.CharField(max_length=120, default="Morning Ride")
    subtitle = models.CharField(max_length=180, blank=True)
    date = models.CharField(max_length=40, blank=True)
    location = models.CharField(max_length=140, blank=True)
    country = models.CharField(max_length=100, blank=True)
    description = models.CharField(max_length=220, blank=True)
    template_name = models.CharField(max_length=60, default="classic_portrait")
    theme_name = models.CharField(max_length=60, default="Gallery Edition")
    activity_type = models.CharField(max_length=20, default="cycling")
    units = models.CharField(max_length=10, default="metric")
    visible_metrics = models.JSONField(default=list)
    theme_settings = models.JSONField(default=dict)
    route_settings = models.JSONField(default=dict)
    photo_settings = models.JSONField(default=dict)
    model3d_settings = models.JSONField(default=dict)
    metrics_data = models.JSONField(default=dict)
    gpx_file = models.FileField(upload_to=project_upload_path)
    photo_file = models.ImageField(upload_to=project_upload_path, blank=True)
    dem_file = models.FileField(upload_to=project_upload_path, blank=True)
    preview_file = models.ImageField(upload_to=preview_upload_path, blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.DRAFT)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self) -> str:
        return self.name

    @property
    def source_filename(self) -> str:
        return Path(self.gpx_file.name).name


class ExportArtifact(models.Model):
    KIND_CHOICES = [
        ("package", "Pacote ZIP"),
        ("pdf", "PDF"),
        ("svg", "SVG"),
        ("png", "PNG"),
        ("jpg", "JPG"),
        ("base", "Base STL"),
        ("route", "Rota STL"),
        ("combined", "Combinado STL"),
        ("project", "Projeto JSON"),
    ]

    project = models.ForeignKey(PrintProject, on_delete=models.CASCADE, related_name="artifacts")
    kind = models.CharField(max_length=20, choices=KIND_CHOICES)
    file = models.FileField(upload_to=artifact_upload_path)
    size_bytes = models.PositiveBigIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["project", "kind"], name="unique_project_artifact")
        ]
        ordering = ["kind"]

    def __str__(self) -> str:
        return f"{self.project.name}: {self.get_kind_display()}"


class ExportJob(models.Model):
    class Status(models.TextChoices):
        QUEUED = "queued", "Na fila"
        RUNNING = "running", "Gerando"
        COMPLETE = "complete", "Concluído"
        FAILED = "failed", "Falhou"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(PrintProject, on_delete=models.CASCADE, related_name="export_jobs")
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="export_jobs",
    )
    session_key = models.CharField(max_length=40, blank=True, db_index=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.QUEUED)
    progress = models.PositiveSmallIntegerField(default=0)
    attempts = models.PositiveSmallIntegerField(default=0)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.project.name}: {self.get_status_display()}"


class Order(models.Model):
    class Product(models.TextChoices):
        DIGITAL = "digital", "Arquivos digitais"
        KIT = "kit", "Kit para montagem"
        FRAMED = "framed", "Quadro montado"

    class Status(models.TextChoices):
        PENDING_PAYMENT = "pending_payment", "Aguardando pagamento"
        PAID = "paid", "Pago"
        PRODUCTION = "production", "Em produção"
        SHIPPED = "shipped", "Enviado"
        COMPLETE = "complete", "Concluído"
        CANCELLED = "cancelled", "Cancelado"

    class PaymentProvider(models.TextChoices):
        MANUAL = "manual", "Pagamento combinado"
        STRIPE = "stripe", "Cartão / Stripe"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(PrintProject, on_delete=models.PROTECT, related_name="orders")
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="orders",
    )
    session_key = models.CharField(max_length=40, blank=True, db_index=True)
    product = models.CharField(max_length=16, choices=Product.choices)
    quantity = models.PositiveSmallIntegerField(default=1)
    customer_name = models.CharField(max_length=120)
    customer_email = models.EmailField()
    customer_phone = models.CharField(max_length=40, blank=True)
    postal_code = models.CharField(max_length=24, blank=True)
    address_line1 = models.CharField(max_length=180, blank=True)
    address_line2 = models.CharField(max_length=180, blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    currency = models.CharField(max_length=3, default="jpy")
    subtotal_amount = models.PositiveIntegerField(default=0)
    shipping_amount = models.PositiveIntegerField(default=0)
    total_amount = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=24, choices=Status.choices, default=Status.PENDING_PAYMENT)
    payment_provider = models.CharField(
        max_length=16, choices=PaymentProvider.choices, default=PaymentProvider.MANUAL
    )
    stripe_session_id = models.CharField(max_length=255, null=True, blank=True, unique=True)
    payment_reference = models.CharField(max_length=255, blank=True)
    carrier = models.CharField(max_length=100, blank=True)
    tracking_number = models.CharField(max_length=120, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    shipped_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.reference} · {self.customer_name}"

    @property
    def reference(self) -> str:
        return f"GPX-{str(self.id).split('-')[0].upper()}"

    @property
    def requires_shipping(self) -> bool:
        return self.product != self.Product.DIGITAL
