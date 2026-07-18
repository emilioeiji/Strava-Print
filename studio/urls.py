from django.urls import path

from studio import views

app_name = "studio"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("projetos/criar/", views.create_project, name="create"),
    path("projetos/<uuid:project_id>/", views.editor, name="editor"),
    path("projetos/<uuid:project_id>/preview/", views.update_preview, name="preview"),
    path("projetos/<uuid:project_id>/preview.jpg", views.preview_image, name="preview-image"),
    path("projetos/<uuid:project_id>/exportar/", views.export_project, name="export"),
    path("projetos/<uuid:project_id>/arquivos/<int:artifact_id>/", views.download_artifact, name="download"),
    path("projetos/<uuid:project_id>/excluir/", views.delete_project, name="delete"),
]
