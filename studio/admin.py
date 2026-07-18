from django.contrib import admin
from django.utils import timezone

from studio.models import ExportArtifact, ExportJob, Order, PrintProject
from studio.services import confirm_order_paid, send_order_email


class ExportArtifactInline(admin.TabularInline):
    model = ExportArtifact
    extra = 0
    readonly_fields = ("kind", "file", "size_bytes", "created_at")


@admin.register(PrintProject)
class PrintProjectAdmin(admin.ModelAdmin):
    list_display = ("name", "owner", "status", "template_name", "updated_at")
    list_filter = ("status", "template_name", "activity_type")
    search_fields = ("name", "title", "location", "gpx_file")
    readonly_fields = ("id", "created_at", "updated_at")
    inlines = (ExportArtifactInline,)


@admin.register(ExportArtifact)
class ExportArtifactAdmin(admin.ModelAdmin):
    list_display = ("project", "kind", "size_bytes", "created_at")
    list_filter = ("kind",)


@admin.register(ExportJob)
class ExportJobAdmin(admin.ModelAdmin):
    list_display = ("project", "status", "progress", "attempts", "created_at")
    list_filter = ("status",)
    readonly_fields = ("id", "created_at", "started_at", "finished_at")


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("reference", "customer_name", "product", "total_amount", "status", "created_at")
    list_filter = ("status", "product", "payment_provider")
    list_editable = ("status",)
    search_fields = ("customer_name", "customer_email", "payment_reference")
    readonly_fields = (
        "id",
        "subtotal_amount",
        "shipping_amount",
        "total_amount",
        "stripe_session_id",
        "paid_at",
        "created_at",
        "updated_at",
    )
    actions = ("confirm_payments", "start_production", "mark_shipped")

    @admin.action(description="Confirmar pagamento dos pedidos selecionados")
    def confirm_payments(self, request, queryset) -> None:
        for order in queryset:
            confirm_order_paid(order, f"admin:{request.user.pk}")

    @admin.action(description="Mover pedidos selecionados para produção")
    def start_production(self, request, queryset) -> None:
        for order in queryset.exclude(status=Order.Status.CANCELLED):
            order.status = Order.Status.PRODUCTION
            order.save(update_fields=["status", "updated_at"])
            send_order_email(order, "studio/emails/order_status.txt", f"Pedido em produção · {order.reference}")

    @admin.action(description="Marcar pedidos selecionados como enviados")
    def mark_shipped(self, request, queryset) -> None:
        for order in queryset.exclude(status=Order.Status.CANCELLED):
            order.status = Order.Status.SHIPPED
            order.shipped_at = timezone.now()
            order.save(update_fields=["status", "shipped_at", "updated_at"])
            send_order_email(order, "studio/emails/order_status.txt", f"Pedido enviado · {order.reference}")
