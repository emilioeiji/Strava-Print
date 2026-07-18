from pathlib import Path
from types import SimpleNamespace

import pytest
from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import Client
from django.test.utils import override_settings
from django.urls import reverse

from studio import payments
from studio.models import ExportArtifact, ExportJob, Order, PrintProject
from studio.services import confirm_order_paid, enqueue_export, generate_exports


def _create_project(client: Client) -> PrintProject:
    upload = SimpleUploadedFile(
        "sample.gpx",
        Path("tests/fixtures/sample.gpx").read_bytes(),
        content_type="application/gpx+xml",
    )
    client.post(reverse("studio:create"), {"name": "Commerce Ride", "gpx_file": upload})
    return PrintProject.objects.get(name="Commerce Ride")


def _physical_order_data() -> dict[str, object]:
    return {
        "product": "framed",
        "quantity": 2,
        "customer_name": "Emilio Eiji",
        "customer_email": "buyer@example.com",
        "customer_phone": "000-0000",
        "postal_code": "693-0001",
        "address_line1": "1-1 Sample Street",
        "address_line2": "",
        "city": "Izumo",
        "state": "Shimane",
        "country": "Japan",
        "notes": "Orange route",
        "payment_provider": "manual",
        "accept_terms": "on",
        "total_amount": 1,
    }


@pytest.mark.django_db
def test_checkout_calculates_price_server_side(client: Client, settings, tmp_path: Path) -> None:
    settings.MEDIA_ROOT = tmp_path
    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
    project = _create_project(client)

    response = client.post(reverse("studio:checkout", args=[project.id]), _physical_order_data())

    order = Order.objects.get()
    assert response.status_code == 302
    assert response.url == reverse("studio:order", args=[order.id])
    assert order.subtotal_amount == settings.PRODUCT_PRICES["framed"] * 2
    assert order.shipping_amount == settings.PRODUCT_SHIPPING["framed"]
    assert order.total_amount != 1
    assert len(mail.outbox) == 1


@pytest.mark.django_db
def test_physical_order_requires_shipping_address(client: Client, settings, tmp_path: Path) -> None:
    settings.MEDIA_ROOT = tmp_path
    project = _create_project(client)
    data = _physical_order_data()
    data["address_line1"] = ""

    response = client.post(reverse("studio:checkout", args=[project.id]), data)

    assert response.status_code == 200
    assert not Order.objects.exists()
    assert "Campo obrigatório" in response.content.decode("utf-8")


@pytest.mark.django_db
def test_order_is_private_and_payment_is_idempotent(client: Client, settings, tmp_path: Path) -> None:
    settings.MEDIA_ROOT = tmp_path
    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
    project = _create_project(client)
    client.post(reverse("studio:checkout", args=[project.id]), _physical_order_data())
    order = Order.objects.get()
    order.payment_provider = Order.PaymentProvider.STRIPE
    order.stripe_session_id = "cs_test_confirmed"
    order.save(update_fields=["payment_provider", "stripe_session_id", "updated_at"])
    mail.outbox.clear()

    assert confirm_order_paid(order, "checkout-session") is True
    assert confirm_order_paid(order, "checkout-session") is False
    assert len(mail.outbox) == 1
    order.refresh_from_db()
    assert order.status == Order.Status.PAID

    other_client = Client()
    assert other_client.get(reverse("studio:order", args=[order.id])).status_code == 404


@pytest.mark.django_db
def test_database_worker_processes_queued_export(client: Client, settings, tmp_path: Path) -> None:
    settings.MEDIA_ROOT = tmp_path
    settings.EXPORT_JOBS_INLINE = False
    project = _create_project(client)
    session_key = client.session.session_key or ""

    job = enqueue_export(project, None, session_key)

    assert job.status == ExportJob.Status.QUEUED
    call_command("process_export_jobs", "--once", verbosity=0)
    job.refresh_from_db()
    assert job.status == ExportJob.Status.COMPLETE
    assert job.progress == 100
    assert ExportArtifact.objects.filter(project=project).count() == 9


@pytest.mark.django_db
@override_settings(
    STORAGES={
        "default": {"BACKEND": "django.core.files.storage.InMemoryStorage"},
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    }
)
def test_export_works_without_local_storage_paths(client: Client) -> None:
    project = _create_project(client)

    artifacts = generate_exports(project)

    assert len(artifacts) == 9
    package = next(artifact for artifact in artifacts if artifact.kind == "package")
    response = client.get(reverse("studio:download", args=[project.id, package.id]))
    assert response.status_code == 200


@pytest.mark.django_db
def test_stripe_webhook_fulfills_order(monkeypatch, client: Client, settings, tmp_path: Path) -> None:
    settings.MEDIA_ROOT = tmp_path
    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
    project = _create_project(client)
    client.post(reverse("studio:checkout", args=[project.id]), _physical_order_data())
    order = Order.objects.get()
    order.payment_provider = Order.PaymentProvider.STRIPE
    order.stripe_session_id = "cs_test_confirmed"
    order.save(update_fields=["payment_provider", "stripe_session_id", "updated_at"])

    event = {
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "id": "cs_test_confirmed",
                "payment_status": "paid",
                "currency": order.currency,
                "amount_total": order.total_amount,
                "metadata": {"order_id": str(order.id)},
            }
        },
    }
    fake_stripe = SimpleNamespace(
        Webhook=SimpleNamespace(construct_event=lambda payload, signature, secret: event)
    )
    monkeypatch.setattr(payments, "_stripe", lambda: fake_stripe)

    payments.handle_webhook(b"{}", "valid-signature")

    order.refresh_from_db()
    assert order.status == Order.Status.PAID
    assert order.payment_reference == "cs_test_confirmed"
