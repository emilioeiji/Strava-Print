"""Dashboard, editor, preview and protected export views."""

from __future__ import annotations

import logging

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.views import LoginView
from django.db import connection
from django.db.models import Q, QuerySet
from django.http import FileResponse, Http404, HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from strava_print.gpx.parser import GPXError
from studio.forms import OrderForm, ProjectCreateForm, ProjectEditorForm, SignUpForm
from studio.models import ExportArtifact, ExportJob, Order, PrintProject
from studio.payments import create_checkout_session, handle_webhook
from studio.services import (
    calculate_order,
    delete_project_files,
    enqueue_export,
    format_money,
    generate_preview,
    metric_cards,
    send_order_email,
    update_activity_metadata,
)

logger = logging.getLogger(__name__)


def health(request: HttpRequest) -> JsonResponse:
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")
        cursor.fetchone()
    return JsonResponse({"status": "ok"})


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


def accessible_orders(request: HttpRequest) -> QuerySet[Order]:
    session_key = _session_key(request)
    query = Q(session_key=session_key)
    if request.user.is_authenticated:
        query |= Q(owner=request.user)
    return Order.objects.filter(query).distinct()


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
            "orders": accessible_orders(request)[:8],
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
            {
                "create_form": form,
                "projects": accessible_projects(request)[:12],
                "orders": accessible_orders(request)[:8],
            },
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
        job = enqueue_export(project, request.user, _session_key(request))
    except (GPXError, OSError, RuntimeError, ValueError) as error:
        logger.exception("Export generation failed for project %s", project.id)
        project.status = PrintProject.Status.ERROR
        project.error_message = str(error)
        project.save(update_fields=["status", "error_message", "updated_at"])
        return JsonResponse({"error": str(error)}, status=422)
    return JsonResponse(
        {
            "status": job.get_status_display(),
            "job_status": job.status,
            "job_url": reverse("studio:export-job", args=[project.id, job.id]),
            "artifacts": [
                {
                    "kind": artifact.kind,
                    "label": artifact.get_kind_display(),
                    "size": artifact.size_bytes,
                    "url": reverse("studio:download", args=[project.id, artifact.id]),
                }
                for artifact in project.artifacts.all()
            ],
        }
    )


def export_job_status(request: HttpRequest, project_id: str, job_id: str) -> JsonResponse:
    project = _project(request, project_id)
    job = get_object_or_404(project.export_jobs, id=job_id)
    artifacts = project.artifacts.all() if job.status == ExportJob.Status.COMPLETE else []
    return JsonResponse(
        {
            "status": job.get_status_display(),
            "job_status": job.status,
            "progress": job.progress,
            "error": job.error_message,
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
    project.preview_file.open("rb")
    return FileResponse(project.preview_file, content_type="image/jpeg")


def download_artifact(request: HttpRequest, project_id: str, artifact_id: int) -> FileResponse:
    project = _project(request, project_id)
    artifact = get_object_or_404(ExportArtifact, project=project, id=artifact_id)
    if not artifact.file:
        raise Http404("Arquivo não encontrado.")
    artifact.file.open("rb")
    return FileResponse(
        artifact.file,
        as_attachment=True,
        filename=artifact.file.name.rsplit("/", 1)[-1],
    )


def delete_project(request: HttpRequest, project_id: str) -> HttpResponse:
    project = _project(request, project_id)
    if request.method != "POST":
        return redirect("studio:editor", project_id=project.id)
    delete_project_files(project)
    project.delete()
    messages.success(request, "Projeto removido.")
    return redirect("studio:dashboard")


def checkout(request: HttpRequest, project_id: str) -> HttpResponse:
    project = _project(request, project_id)
    initial = {}
    if request.user.is_authenticated:
        initial = {"customer_name": request.user.get_full_name(), "customer_email": request.user.email}
    form = OrderForm(request.POST or None, initial=initial)
    if request.method == "POST" and form.is_valid():
        order = form.save(commit=False)
        order.project = project
        order.session_key = _session_key(request)
        order.owner = request.user if request.user.is_authenticated else None
        calculate_order(order)
        order.save()
        send_order_email(order, "studio/emails/order_created.txt", f"Pedido recebido · {order.reference}")
        if order.payment_provider == Order.PaymentProvider.STRIPE:
            try:
                return redirect(create_checkout_session(order, request))
            except RuntimeError as error:
                messages.error(request, str(error))
        return redirect("studio:order", order_id=order.id)
    products = [
        {
            "value": value,
            "label": label,
            "price": format_money(settings.PRODUCT_PRICES[value], settings.STORE_CURRENCY),
            "shipping": format_money(settings.PRODUCT_SHIPPING[value], settings.STORE_CURRENCY)
            if settings.PRODUCT_SHIPPING[value]
            else "Sem envio",
        }
        for value, label in Order.Product.choices
    ]
    return render(
        request,
        "studio/checkout.html",
        {"project": project, "form": form, "products": products},
    )


def order_detail(request: HttpRequest, order_id: str) -> HttpResponse:
    order = get_object_or_404(accessible_orders(request), id=order_id)
    return render(
        request,
        "studio/order.html",
        {
            "order": order,
            "total": format_money(order.total_amount, order.currency),
            "payment_instructions": settings.MANUAL_PAYMENT_INSTRUCTIONS,
        },
    )


def order_success(request: HttpRequest, order_id: str) -> HttpResponse:
    order = get_object_or_404(accessible_orders(request), id=order_id)
    messages.success(request, "Retorno do Stripe recebido. A confirmação segura será feita pelo webhook.")
    return redirect("studio:order", order_id=order.id)


@csrf_exempt
def stripe_webhook(request: HttpRequest) -> HttpResponse:
    if request.method != "POST":
        return HttpResponse(status=405)
    try:
        handle_webhook(request.body, request.headers.get("Stripe-Signature", ""))
    except (RuntimeError, ValueError) as error:
        logger.warning("Stripe webhook rejected: %s", error)
        return HttpResponse(status=400)
    return HttpResponse(status=200)


def legal_page(request: HttpRequest, page: str) -> HttpResponse:
    if page not in {"termos", "privacidade"}:
        raise Http404
    return render(request, f"studio/{page}.html")


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


class StudioLoginView(LoginView):
    template_name = "registration/login.html"

    def form_valid(self, form):
        session_key = _session_key(self.request)
        response = super().form_valid(form)
        PrintProject.objects.filter(session_key=session_key, owner__isnull=True).update(
            owner=self.request.user
        )
        Order.objects.filter(session_key=session_key, owner__isnull=True).update(owner=self.request.user)
        return response
