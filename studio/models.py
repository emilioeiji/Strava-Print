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
