# Generated for the initial GPX Print Studio schema.

import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models

import studio.models


class Migration(migrations.Migration):
    initial = True
    dependencies = [("auth", "0012_alter_user_first_name_max_length")]
    operations = [
        migrations.CreateModel(
            name="PrintProject",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("session_key", models.CharField(blank=True, db_index=True, max_length=40)),
                ("name", models.CharField(default="Nova atividade", max_length=120)),
                ("title", models.CharField(default="Morning Ride", max_length=120)),
                ("subtitle", models.CharField(blank=True, max_length=180)),
                ("date", models.CharField(blank=True, max_length=40)),
                ("location", models.CharField(blank=True, max_length=140)),
                ("country", models.CharField(blank=True, max_length=100)),
                ("description", models.CharField(blank=True, max_length=220)),
                ("template_name", models.CharField(default="classic_portrait", max_length=60)),
                ("theme_name", models.CharField(default="Gallery Edition", max_length=60)),
                ("activity_type", models.CharField(default="cycling", max_length=20)),
                ("units", models.CharField(default="metric", max_length=10)),
                ("visible_metrics", models.JSONField(default=list)),
                ("theme_settings", models.JSONField(default=dict)),
                ("route_settings", models.JSONField(default=dict)),
                ("photo_settings", models.JSONField(default=dict)),
                ("model3d_settings", models.JSONField(default=dict)),
                ("metrics_data", models.JSONField(default=dict)),
                ("gpx_file", models.FileField(upload_to=studio.models.project_upload_path)),
                ("photo_file", models.ImageField(blank=True, upload_to=studio.models.project_upload_path)),
                ("dem_file", models.FileField(blank=True, upload_to=studio.models.project_upload_path)),
                ("preview_file", models.ImageField(blank=True, upload_to=studio.models.preview_upload_path)),
                ("status", models.CharField(choices=[("draft", "Rascunho"), ("ready", "Pronto"), ("processing", "Gerando"), ("complete", "Concluído"), ("error", "Erro")], default="draft", max_length=16)),
                ("error_message", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("owner", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="print_projects", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-updated_at"]},
        ),
        migrations.CreateModel(
            name="ExportArtifact",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("kind", models.CharField(choices=[("package", "Pacote ZIP"), ("pdf", "PDF"), ("svg", "SVG"), ("png", "PNG"), ("jpg", "JPG"), ("base", "Base STL"), ("route", "Rota STL"), ("combined", "Combinado STL"), ("project", "Projeto JSON")], max_length=20)),
                ("file", models.FileField(upload_to=studio.models.artifact_upload_path)),
                ("size_bytes", models.PositiveBigIntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("project", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="artifacts", to="studio.printproject")),
            ],
            options={"ordering": ["kind"]},
        ),
        migrations.AddConstraint(
            model_name="exportartifact",
            constraint=models.UniqueConstraint(fields=("project", "kind"), name="unique_project_artifact"),
        ),
    ]
