from django.urls import path

from studio import views

app_name = "studio"

urlpatterns = [
    path("health/", views.health, name="health"),
    path("", views.dashboard, name="dashboard"),
    path("projetos/criar/", views.create_project, name="create"),
    path("projetos/<uuid:project_id>/", views.editor, name="editor"),
    path("projetos/<uuid:project_id>/preview/", views.update_preview, name="preview"),
    path("projetos/<uuid:project_id>/preview.jpg", views.preview_image, name="preview-image"),
    path("projetos/<uuid:project_id>/exportar/", views.export_project, name="export"),
    path("projetos/<uuid:project_id>/jobs/<uuid:job_id>/", views.export_job_status, name="export-job"),
    path("projetos/<uuid:project_id>/arquivos/<int:artifact_id>/", views.download_artifact, name="download"),
    path("projetos/<uuid:project_id>/comprar/", views.checkout, name="checkout"),
    path("projetos/<uuid:project_id>/excluir/", views.delete_project, name="delete"),
    path("pedidos/<uuid:order_id>/", views.order_detail, name="order"),
    path("pedidos/<uuid:order_id>/sucesso/", views.order_success, name="order-success"),
    path("integracoes/stripe/webhook/", views.stripe_webhook, name="stripe-webhook"),
    path("legal/<slug:page>/", views.legal_page, name="legal"),
]
