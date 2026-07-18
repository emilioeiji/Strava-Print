"""Optional Stripe Checkout integration kept behind environment configuration."""

from __future__ import annotations

from django.conf import settings
from django.http import HttpRequest
from django.urls import reverse

from studio.models import Order
from studio.services import confirm_order_paid


def _stripe():
    if not settings.STRIPE_ENABLED:
        raise RuntimeError("Stripe não está configurado nesta instalação.")
    try:
        import stripe
    except ImportError as error:
        raise RuntimeError("Instale o extra .[production] para habilitar pagamentos Stripe.") from error
    stripe.api_key = settings.STRIPE_SECRET_KEY
    return stripe


def create_checkout_session(order: Order, request: HttpRequest) -> str:
    stripe = _stripe()
    line_items = [
        {
            "price_data": {
                "currency": order.currency,
                "unit_amount": order.subtotal_amount // order.quantity,
                "product_data": {
                    "name": order.get_product_display(),
                    "description": f"Projeto {order.project.name} · {order.reference}",
                },
            },
            "quantity": order.quantity,
        }
    ]
    if order.shipping_amount:
        line_items.append(
            {
                "price_data": {
                    "currency": order.currency,
                    "unit_amount": order.shipping_amount,
                    "product_data": {"name": "Envio"},
                },
                "quantity": 1,
            }
        )
    success = request.build_absolute_uri(reverse("studio:order-success", args=[order.id]))
    cancel = request.build_absolute_uri(reverse("studio:order", args=[order.id]))
    session = stripe.checkout.Session.create(
        mode="payment",
        line_items=line_items,
        customer_email=order.customer_email,
        client_reference_id=str(order.id),
        metadata={"order_id": str(order.id), "order_reference": order.reference},
        success_url=f"{success}?session_id={{CHECKOUT_SESSION_ID}}",
        cancel_url=cancel,
    )
    order.stripe_session_id = session.id
    order.save(update_fields=["stripe_session_id", "updated_at"])
    return session.url


def handle_webhook(payload: bytes, signature: str) -> None:
    stripe = _stripe()
    try:
        event = stripe.Webhook.construct_event(payload, signature, settings.STRIPE_WEBHOOK_SECRET)
    except stripe.error.SignatureVerificationError as error:
        raise ValueError("Assinatura do webhook Stripe inválida.") from error
    event_type = event["type"]
    session = event["data"]["object"]
    if event_type in {"checkout.session.completed", "checkout.session.async_payment_succeeded"}:
        if session.get("payment_status") == "unpaid":
            return
        order_id = session.get("metadata", {}).get("order_id")
        if not order_id:
            return
        try:
            order = Order.objects.get(
                id=order_id,
                stripe_session_id=session["id"],
                payment_provider=Order.PaymentProvider.STRIPE,
            )
        except Order.DoesNotExist as error:
            raise ValueError("O webhook não corresponde a um pedido Stripe conhecido.") from error
        if session.get("currency") and session["currency"].lower() != order.currency.lower():
            raise ValueError("A moeda recebida do Stripe não corresponde ao pedido.")
        if session.get("amount_total") is not None and session["amount_total"] != order.total_amount:
            raise ValueError("O valor recebido do Stripe não corresponde ao pedido.")
        confirm_order_paid(order, session["id"])
    elif event_type == "checkout.session.async_payment_failed":
        order_id = session.get("metadata", {}).get("order_id")
        if order_id:
            Order.objects.filter(id=order_id, paid_at__isnull=True).update(
                status=Order.Status.PENDING_PAYMENT
            )
