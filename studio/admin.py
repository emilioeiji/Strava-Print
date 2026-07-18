from django.contrib import admin

from studio.models import ExportArtifact, PrintProject


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
