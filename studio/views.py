"""Dashboard, editor, preview and protected export views."""

from __future__ import annotations

import logging
from pathlib import Path

from django.contrib import messages
from django.contrib.auth import login
from django.db.models import Q, QuerySet
from django.http import FileResponse, Http404, HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views import View

from strava_print.gpx.parser import GPXError
from studio.forms import ProjectCreateForm, ProjectEditorForm, SignUpForm
from studio.models import ExportArtifact, PrintProject
from studio.services import (
    delete_project_files,
    generate_exports,
    generate_preview,
    metric_cards,
    update_activity_metadata,
)

logger = logging.getLogger(__name__)


def _session_key(request: HttpRequest) -> str:
    if not request.session.session_key:
        request.session.create()
    return request.session.session_key or ""


def accessible_projects(request: HttpRequest) -> QuerySet[PrintProject]:
    session_key = _session_key(request)
    query = Q(session_key=session_key)
    if request.user.is_authenticated:
        query |= Q(owner=request.user)
    return PrintProject.objects.filter(query).distinct()


def _project(request: HttpRequest, project_id: str) -> PrintProject:
    return get_object_or_404(accessible_projects(request), id=project_id)


def _form_errors(form: ProjectEditorForm) -> dict[str, list[str]]:
    return {field: [str(error) for error in errors] for field, errors in form.errors.items()}


def dashboard(request: HttpRequest) -> HttpResponse:
    return render(
        request,
        "studio/dashboard.html",
        {
            "create_form": ProjectCreateForm(),
            "projects": accessible_projects(request)[:12],
        },
    )


def create_project(request: HttpRequest) -> HttpResponse:
    if request.method != "POST":
        return redirect("studio:dashboard")
    form = ProjectCreateForm(request.POST, request.FILES)
    if not form.is_valid():
        return render(
            request,
            "studio/dashboard.html",
            {"create_form": form, "projects": accessible_projects(request)[:12]},
            status=400,
        )
    project = form.save(commit=False)
    project.session_key = _session_key(request)
    if request.user.is_authenticated:
        project.owner = request.user
    project.visible_metrics = ["distance", "moving_time", "elevation_gain", "average_speed"]
    project.save()
    try:
        update_activity_metadata(project)
        generate_preview(project)
    except (GPXError, OSError, ValueError) as error:
        project.status = PrintProject.Status.ERROR
        project.error_message = str(error)
        project.save(update_fields=["status", "error_message", "updated_at"])
        messages.error(request, f"O projeto foi criado, mas o GPX precisa de atenção: {error}")
    return redirect("studio:editor", project_id=project.id)


def editor(request: HttpRequest, project_id: str) -> HttpResponse:
    project = _project(request, project_id)
    return render(
        request,
        "studio/editor.html",
        {
            "project": project,
            "form": ProjectEditorForm(instance=project),
            "metrics": metric_cards(project),
            "artifacts": project.artifacts.all(),
        },
    )


def update_preview(request: HttpRequest, project_id: str) -> JsonResponse:
    project = _project(request, project_id)
    if request.method != "POST":
        return JsonResponse({"error": "Método não permitido."}, status=405)
    form = ProjectEditorForm(request.POST, request.FILES, instance=project)
    if not form.is_valid():
        return JsonResponse({"errors": _form_errors(form)}, status=400)
    previous_gpx = project.gpx_file.name
    try:
        project = form.save()
        if project.gpx_file.name != previous_gpx:
            update_activity_metadata(project)
        generate_preview(project)
    except (GPXError, OSError, RuntimeError, ValueError) as error:
        logger.exception("Preview generation failed for project %s", project.id)
        project.status = PrintProject.Status.ERROR
        project.error_message = str(error)
        project.save(update_fields=["status", "error_message", "updated_at"])
        return JsonResponse({"error": str(error)}, status=422)
    return JsonResponse(
        {
            "preview_url": reverse("studio:preview-image", args=[project.id]),
            "metrics": metric_cards(project),
            "status": project.get_status_display(),
            "updated_at": project.updated_at.isoformat(),
        }
    )


def export_project(request: HttpRequest, project_id: str) -> JsonResponse:
    project = _project(request, project_id)
    if request.method != "POST":
        return JsonResponse({"error": "Método não permitido."}, status=405)
    form = ProjectEditorForm(request.POST, request.FILES, instance=project)
    if not form.is_valid():
        return JsonResponse({"errors": _form_errors(form)}, status=400)
    try:
        project = form.save()
        project.status = PrintProject.Status.PROCESSING
        project.save(update_fields=["status", "updated_at"])
        generate_preview(project)
        artifacts = generate_exports(project)
    except (GPXError, OSError, RuntimeError, ValueError) as error:
        logger.exception("Export generation failed for project %s", project.id)
        project.status = PrintProject.Status.ERROR
        project.error_message = str(error)
        project.save(update_fields=["status", "error_message", "updated_at"])
        return JsonResponse({"error": str(error)}, status=422)
    return JsonResponse(
        {
            "status": "Concluído",
            "artifacts": [
                {
                    "kind": artifact.kind,
                    "label": artifact.get_kind_display(),
                    "size": artifact.size_bytes,
                    "url": reverse("studio:download", args=[project.id, artifact.id]),
                }
                for artifact in artifacts
            ],
        }
    )


def preview_image(request: HttpRequest, project_id: str) -> FileResponse:
    project = _project(request, project_id)
    if not project.preview_file:
        raise Http404("Pré-visualização ainda não gerada.")
    return FileResponse(open(project.preview_file.path, "rb"), content_type="image/jpeg")


def download_artifact(request: HttpRequest, project_id: str, artifact_id: int) -> FileResponse:
    project = _project(request, project_id)
    artifact = get_object_or_404(ExportArtifact, project=project, id=artifact_id)
    path = Path(artifact.file.path)
    if not path.exists():
        raise Http404("Arquivo não encontrado.")
    return FileResponse(open(path, "rb"), as_attachment=True, filename=path.name)


def delete_project(request: HttpRequest, project_id: str) -> HttpResponse:
    project = _project(request, project_id)
    if request.method != "POST":
        return redirect("studio:editor", project_id=project.id)
    delete_project_files(project)
    project.delete()
    messages.success(request, "Projeto removido.")
    return redirect("studio:dashboard")


class SignUpView(View):
    template_name = "registration/signup.html"

    def get(self, request: HttpRequest) -> HttpResponse:
        return render(request, self.template_name, {"form": SignUpForm()})

    def post(self, request: HttpRequest) -> HttpResponse:
        form = SignUpForm(request.POST)
        if not form.is_valid():
            return render(request, self.template_name, {"form": form}, status=400)
        session_key = _session_key(request)
        user = form.save()
        PrintProject.objects.filter(session_key=session_key, owner__isnull=True).update(owner=user)
        login(request, user)
        return redirect("studio:dashboard")
