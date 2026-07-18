import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("studio", "0001_initial"),
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [
        migrations.CreateModel(
            name="ExportJob",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("session_key", models.CharField(blank=True, db_index=True, max_length=40)),
                ("status", models.CharField(choices=[("queued", "Na fila"), ("running", "Gerando"), ("complete", "Concluído"), ("failed", "Falhou")], default="queued", max_length=16)),
                ("progress", models.PositiveSmallIntegerField(default=0)),
                ("attempts", models.PositiveSmallIntegerField(default=0)),
                ("error_message", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("started_at", models.DateTimeField(blank=True, null=True)),
                ("finished_at", models.DateTimeField(blank=True, null=True)),
                ("project", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="export_jobs", to="studio.printproject")),
                ("requested_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="export_jobs", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="Order",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("session_key", models.CharField(blank=True, db_index=True, max_length=40)),
                ("product", models.CharField(choices=[("digital", "Arquivos digitais"), ("kit", "Kit para montagem"), ("framed", "Quadro montado")], max_length=16)),
                ("quantity", models.PositiveSmallIntegerField(default=1)),
                ("customer_name", models.CharField(max_length=120)),
                ("customer_email", models.EmailField(max_length=254)),
                ("customer_phone", models.CharField(blank=True, max_length=40)),
                ("postal_code", models.CharField(blank=True, max_length=24)),
                ("address_line1", models.CharField(blank=True, max_length=180)),
                ("address_line2", models.CharField(blank=True, max_length=180)),
                ("city", models.CharField(blank=True, max_length=100)),
                ("state", models.CharField(blank=True, max_length=100)),
                ("country", models.CharField(blank=True, max_length=100)),
                ("notes", models.TextField(blank=True)),
                ("currency", models.CharField(default="jpy", max_length=3)),
                ("subtotal_amount", models.PositiveIntegerField(default=0)),
                ("shipping_amount", models.PositiveIntegerField(default=0)),
                ("total_amount", models.PositiveIntegerField(default=0)),
                ("status", models.CharField(choices=[("pending_payment", "Aguardando pagamento"), ("paid", "Pago"), ("production", "Em produção"), ("shipped", "Enviado"), ("complete", "Concluído"), ("cancelled", "Cancelado")], default="pending_payment", max_length=24)),
                ("payment_provider", models.CharField(choices=[("manual", "Pagamento combinado"), ("stripe", "Cartão / Stripe")], default="manual", max_length=16)),
                ("stripe_session_id", models.CharField(blank=True, max_length=255, null=True, unique=True)),
                ("payment_reference", models.CharField(blank=True, max_length=255)),
                ("paid_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("owner", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="orders", to=settings.AUTH_USER_MODEL)),
                ("project", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="orders", to="studio.printproject")),
            ],
            options={"ordering": ["-created_at"]},
        ),
    ]
