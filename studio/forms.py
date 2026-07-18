"""Validated forms used by the project dashboard and editor."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from django import forms
from django.conf import settings
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from strava_print.layouts.templates import available_templates
from strava_print.layouts.themes import MATERIALS, ROUTE_COLORS, THEMES
from studio.models import Order, PrintProject

DEFAULT_METRICS = ["distance", "moving_time", "elevation_gain", "average_speed"]
METRIC_CHOICES = [
    ("distance", "Distância"),
    ("moving_time", "Tempo em movimento"),
    ("duration", "Duração"),
    ("elevation_gain", "Ganho de elevação"),
    ("altitude_max", "Altitude máxima"),
    ("average_speed", "Velocidade média"),
    ("max_speed", "Velocidade máxima"),
    ("average_pace", "Ritmo médio"),
]


def _validate_upload(upload: Any, extensions: set[str], max_mb: int, label: str) -> Any:
    if not upload:
        return upload
    extension = Path(upload.name).suffix.lower()
    if extension not in extensions:
        allowed = ", ".join(sorted(extensions))
        raise forms.ValidationError(f"{label}: formato inválido. Use {allowed}.")
    if upload.size > max_mb * 1024 * 1024:
        raise forms.ValidationError(f"{label}: o arquivo deve ter no máximo {max_mb} MB.")
    return upload


class SignUpForm(UserCreationForm):
    email = forms.EmailField(label="E-mail")

    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2")


class ProjectCreateForm(forms.ModelForm):
    class Meta:
        model = PrintProject
        fields = ("name", "gpx_file")
        labels = {"name": "Nome do projeto", "gpx_file": "Arquivo GPX"}
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": "Morning Ride"}),
            "gpx_file": forms.FileInput(attrs={"accept": ".gpx"}),
        }

    def clean_gpx_file(self) -> Any:
        return _validate_upload(self.cleaned_data.get("gpx_file"), {".gpx"}, 50, "GPX")


class ProjectEditorForm(forms.Form):
    name = forms.CharField(max_length=120, label="Nome do projeto")
    title = forms.CharField(max_length=120, label="Título")
    subtitle = forms.CharField(max_length=180, required=False, label="Subtítulo")
    date = forms.CharField(max_length=40, required=False, label="Data")
    location = forms.CharField(max_length=140, required=False, label="Local")
    country = forms.CharField(max_length=100, required=False, label="País")
    description = forms.CharField(max_length=220, required=False, label="Descrição")
    template_name = forms.ChoiceField(label="Layout")
    theme_name = forms.ChoiceField(choices=[(name, name) for name in THEMES], label="Tema")
    activity_type = forms.ChoiceField(
        choices=[
            ("cycling", "Ciclismo"),
            ("running", "Corrida"),
            ("walking", "Caminhada"),
            ("hiking", "Trilha"),
            ("generic", "Genérica"),
        ],
        label="Atividade",
    )
    units = forms.ChoiceField(
        choices=[("metric", "Métrico"), ("imperial", "Imperial")],
        widget=forms.RadioSelect,
        label="Unidades",
    )
    visible_metrics = forms.MultipleChoiceField(
        choices=METRIC_CHOICES,
        widget=forms.CheckboxSelectMultiple,
        label="Métricas visíveis",
    )
    material = forms.ChoiceField(choices=[(name, name) for name in MATERIALS], label="Material")
    route_color = forms.ChoiceField(
        choices=[(name, name) for name in ROUTE_COLORS], label="Cor da rota"
    )
    route_rotation = forms.FloatField(
        min_value=-180,
        max_value=180,
        label="Rotação da rota",
        widget=forms.NumberInput(attrs={"type": "range", "step": "1"}),
    )
    model_mode = forms.ChoiceField(
        choices=[("flat_map", "Mapa plano"), ("terrain", "Terreno DEM")], label="Modelo 3D"
    )
    width_mm = forms.FloatField(min_value=60, max_value=200, label="Largura da peça")
    base_thickness_mm = forms.FloatField(min_value=0.8, max_value=5, label="Espessura da base")
    route_width_mm = forms.FloatField(min_value=0.8, max_value=4, label="Largura da rota")
    route_height_mm = forms.FloatField(min_value=0.6, max_value=4, label="Altura da rota")
    terrain_height_mm = forms.FloatField(min_value=1, max_value=24, label="Altura do relevo")
    terrain_route_style = forms.ChoiceField(
        choices=[("inlay", "Encaixe sem suporte"), ("tube", "Tubo sobre o terreno")],
        label="Construção da rota",
    )
    inlay_clearance_mm = forms.FloatField(
        min_value=0, max_value=0.5, label="Folga do encaixe"
    )
    photo_x = forms.FloatField(min_value=0, max_value=100, label="Posição horizontal")
    photo_y = forms.FloatField(min_value=0, max_value=100, label="Posição vertical")
    photo_zoom = forms.FloatField(min_value=1, max_value=4, label="Zoom")
    photo_rotation = forms.FloatField(min_value=-180, max_value=180, label="Rotação da foto")
    photo_brightness = forms.FloatField(min_value=0.2, max_value=2, label="Brilho")
    photo_contrast = forms.FloatField(min_value=0.2, max_value=2, label="Contraste")
    photo_grayscale = forms.BooleanField(required=False, label="Preto e branco")
    photo_overlay = forms.ChoiceField(
        choices=[("none", "Sem overlay"), ("dark", "Escuro"), ("light", "Claro")],
        label="Overlay",
    )
    photo_rounded = forms.BooleanField(required=False, label="Cantos arredondados")
    gpx_file = forms.FileField(required=False, label="Substituir GPX")
    photo_file = forms.ImageField(required=False, label="Fotografia")
    dem_file = forms.FileField(required=False, label="DEM GeoTIFF")

    def __init__(self, *args: Any, instance: PrintProject, **kwargs: Any) -> None:
        self.instance = instance
        super().__init__(*args, **kwargs)
        self.fields["template_name"].choices = [(name, name) for name in available_templates()]
        if not self.is_bound:
            model = {
                "mode": "terrain" if instance.dem_file else "flat_map",
                "width_mm": 130.0,
                "base_thickness_mm": 1.6,
                "route_width_mm": 1.8,
                "route_height_mm": 1.2,
                "terrain_height_mm": 8.0,
                "terrain_route_style": "inlay",
                "inlay_clearance_mm": 0.15,
                **instance.model3d_settings,
            }
            photo = {
                "x": 50.0,
                "y": 50.0,
                "zoom": 1.0,
                "rotation": 0.0,
                "brightness": 1.0,
                "contrast": 1.0,
                "grayscale": False,
                "overlay": "none",
                "rounded": False,
                **instance.photo_settings,
            }
            self.initial.update(
                {
                    "name": instance.name,
                    "title": instance.title,
                    "subtitle": instance.subtitle,
                    "date": instance.date,
                    "location": instance.location,
                    "country": instance.country,
                    "description": instance.description,
                    "template_name": instance.template_name,
                    "theme_name": instance.theme_name,
                    "activity_type": instance.activity_type,
                    "units": instance.units,
                    "visible_metrics": instance.visible_metrics or DEFAULT_METRICS,
                    "material": instance.theme_settings.get("material_name", next(iter(MATERIALS))),
                    "route_color": instance.theme_settings.get("route_color_name", next(iter(ROUTE_COLORS))),
                    "route_rotation": instance.route_settings.get("rotation", 0),
                    "model_mode": model["mode"],
                    "width_mm": model["width_mm"],
                    "base_thickness_mm": model["base_thickness_mm"],
                    "route_width_mm": model["route_width_mm"],
                    "route_height_mm": model["route_height_mm"],
                    "terrain_height_mm": model["terrain_height_mm"],
                    "terrain_route_style": model["terrain_route_style"],
                    "inlay_clearance_mm": model["inlay_clearance_mm"],
                    "photo_x": photo["x"],
                    "photo_y": photo["y"],
                    "photo_zoom": photo["zoom"],
                    "photo_rotation": photo["rotation"],
                    "photo_brightness": photo["brightness"],
                    "photo_contrast": photo["contrast"],
                    "photo_grayscale": photo["grayscale"],
                    "photo_overlay": photo["overlay"],
                    "photo_rounded": photo["rounded"],
                }
            )

    def clean_visible_metrics(self) -> list[str]:
        metrics = self.cleaned_data["visible_metrics"]
        if len(metrics) > 5:
            raise forms.ValidationError("Escolha no máximo cinco métricas.")
        return metrics

    def clean_gpx_file(self) -> Any:
        return _validate_upload(self.cleaned_data.get("gpx_file"), {".gpx"}, 50, "GPX")

    def clean_photo_file(self) -> Any:
        return _validate_upload(
            self.cleaned_data.get("photo_file"), {".jpg", ".jpeg", ".png", ".webp"}, 25, "Foto"
        )

    def clean_dem_file(self) -> Any:
        return _validate_upload(
            self.cleaned_data.get("dem_file"), {".tif", ".tiff"}, 250, "DEM"
        )

    def clean(self) -> dict[str, Any]:
        cleaned = super().clean()
        mode = cleaned.get("model_mode")
        if mode == "terrain" and not (cleaned.get("dem_file") or self.instance.dem_file):
            self.add_error("dem_file", "Envie um GeoTIFF para usar o modo Terrain.")
        return cleaned

    def save(self) -> PrintProject:
        data = self.cleaned_data
        project = self.instance
        for field in (
            "name",
            "title",
            "subtitle",
            "date",
            "location",
            "country",
            "description",
            "activity_type",
            "units",
        ):
            setattr(project, field, data[field])
        project.template_name = data["template_name"]
        project.theme_name = data["theme_name"]
        project.visible_metrics = data["visible_metrics"]
        project.theme_settings = {
            "material_name": data["material"],
            "route_color_name": data["route_color"],
        }
        project.route_settings = {"rotation": data["route_rotation"]}
        project.model3d_settings = {
            "mode": data["model_mode"],
            "width_mm": data["width_mm"],
            "base_thickness_mm": data["base_thickness_mm"],
            "route_width_mm": data["route_width_mm"],
            "route_height_mm": data["route_height_mm"],
            "terrain_height_mm": data["terrain_height_mm"],
            "terrain_route_style": data["terrain_route_style"],
            "inlay_clearance_mm": data["inlay_clearance_mm"],
        }
        project.photo_settings = {
            "x": data["photo_x"],
            "y": data["photo_y"],
            "zoom": data["photo_zoom"],
            "rotation": data["photo_rotation"],
            "brightness": data["photo_brightness"],
            "contrast": data["photo_contrast"],
            "grayscale": data["photo_grayscale"],
            "overlay": data["photo_overlay"],
            "rounded": data["photo_rounded"],
        }
        for field in ("gpx_file", "photo_file", "dem_file"):
            if data.get(field):
                setattr(project, field, data[field])
        project.save()
        return project


class OrderForm(forms.ModelForm):
    accept_terms = forms.BooleanField(
        label="Li e aceito os termos de venda e a política de privacidade."
    )

    class Meta:
        model = Order
        fields = (
            "product",
            "quantity",
            "customer_name",
            "customer_email",
            "customer_phone",
            "postal_code",
            "address_line1",
            "address_line2",
            "city",
            "state",
            "country",
            "notes",
            "payment_provider",
        )
        labels = {
            "product": "Produto",
            "quantity": "Quantidade",
            "customer_name": "Nome completo",
            "customer_email": "E-mail",
            "customer_phone": "Telefone",
            "postal_code": "Código postal",
            "address_line1": "Endereço",
            "address_line2": "Complemento",
            "city": "Cidade",
            "state": "Estado / província",
            "country": "País",
            "notes": "Observações",
            "payment_provider": "Pagamento",
        }
        widgets = {
            "product": forms.RadioSelect,
            "quantity": forms.NumberInput(attrs={"min": 1, "max": 10}),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        providers = [(Order.PaymentProvider.MANUAL, "Combinar pagamento")]
        if settings.STRIPE_ENABLED:
            providers.insert(0, (Order.PaymentProvider.STRIPE, "Cartão via Stripe"))
        self.fields["payment_provider"].choices = providers
        self.fields["quantity"].min_value = 1
        self.fields["quantity"].max_value = 10
        if not self.is_bound:
            self.initial.setdefault("product", Order.Product.FRAMED)
            self.initial.setdefault("quantity", 1)
            self.initial.setdefault("country", "Japan")

    def clean(self) -> dict[str, Any]:
        cleaned = super().clean()
        product = cleaned.get("product")
        if product and product != Order.Product.DIGITAL:
            for field in ("postal_code", "address_line1", "city", "country"):
                if not cleaned.get(field):
                    self.add_error(field, "Campo obrigatório para produtos físicos.")
        if cleaned.get("payment_provider") == Order.PaymentProvider.STRIPE and not settings.STRIPE_ENABLED:
            self.add_error("payment_provider", "Pagamento Stripe ainda não está configurado.")
        return cleaned
