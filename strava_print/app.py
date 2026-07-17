"""Local Streamlit editor for premium GPX terrain posters."""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path

import streamlit as st

from strava_print.domain.models import Project
from strava_print.export.package import export_all
from strava_print.gpx.parser import GPXError, parse_gpx
from strava_print.layouts.templates import available_templates, load_template
from strava_print.layouts.themes import MATERIALS, ROUTE_COLORS, THEMES
from strava_print.renderers.preview_renderer import render_framed_preview, render_mounted_preview
from strava_print.renderers.raster_renderer import render_image

logger = logging.getLogger(__name__)

st.set_page_config(page_title="GPX Print Studio", page_icon="◉", layout="wide")
st.markdown(
    """
    <style>
    .stApp { background: #ece9e2; color: #1d2428; }
    [data-testid="stSidebar"] { background: #e3dfd7; }
    [data-testid="stFileUploader"] { border-color: #596267; }
    [data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"],
    [data-testid="stSidebar"] [data-baseweb="select"] > div,
    [data-testid="stSidebar"] input { background: #fbfaf7 !important; color: #1d2428 !important; }
    [data-testid="stSidebar"] [data-baseweb="select"] *,
    [data-testid="stSidebar"] input::placeholder { color: #697176 !important; }
    .block-container { padding-top: 1.4rem; max-width: 1440px; }
    h1 { font-family: Arial Narrow, sans-serif; letter-spacing: 0; }
    </style>
    """,
    unsafe_allow_html=True,
)
st.title("GPX Print Studio")
st.caption("Editor local de pôster e relevo 3D personalizado")

with st.sidebar:
    st.subheader("Fontes")
    gpx_upload = st.file_uploader("Arquivo GPX", type=["gpx"])
    photo_upload = st.file_uploader("Fotografia opcional", type=["jpg", "jpeg", "png", "webp"])
    dem_upload = st.file_uploader("DEM GeoTIFF para relevo", type=["tif", "tiff"])
    st.divider()
    st.subheader("Composição")
    template_options = available_templates()
    default_template = template_options.index("classic_portrait")
    template_name = st.selectbox("Layout", template_options, index=default_template)
    theme_name = st.selectbox("Tema", list(THEMES), index=0)
    material_name = st.selectbox("Material da peça", list(MATERIALS))
    route_color_name = st.selectbox("Cor da rota", list(ROUTE_COLORS))
    title = st.text_input("Título", "Morning Ride")
    date = st.text_input("Data", "")
    location = st.text_input("Local", "")
    country = st.text_input("País", "")
    activity_type = st.selectbox(
        "Atividade", ["cycling", "running", "walking", "hiking", "generic"]
    )
    units = st.radio("Unidades", ["metric", "imperial"], horizontal=True)
    map_rotation = st.slider("Rotação da rota", -180, 180, 0)
    st.divider()
    st.subheader("Peça 3D")
    route_width = st.slider("Largura da rota (mm)", 0.8, 4.0, 1.8, 0.1)
    route_height = st.slider("Altura da rota (mm)", 0.6, 3.0, 1.2, 0.1)
    terrain_height = st.slider("Altura do relevo (mm)", 2.0, 20.0, 8.0, 0.5)
    support_free_inlay = st.toggle("Encaixe da rota sem suporte", value=True)
    inlay_clearance = st.slider("Folga do encaixe por lado (mm)", 0.05, 0.35, 0.15, 0.05)

if not gpx_upload:
    st.info("Envie um arquivo GPX para criar a primeira composição.")
    st.stop()

with tempfile.TemporaryDirectory() as directory:
    work = Path(directory)
    gpx_path = work / "activity.gpx"
    gpx_path.write_bytes(gpx_upload.getvalue())
    try:
        activity = parse_gpx(gpx_path)
    except GPXError as error:
        st.error(str(error))
        st.stop()
    project = Project(
        source_gpx=gpx_upload.name,
        template=template_name,
        title=title,
        date=date,
        location=location,
        country=country,
        activity_type=activity_type,
        units=units,
        theme={
            **THEMES[theme_name],
            "material": MATERIALS[material_name],
            "accent": ROUTE_COLORS[route_color_name],
        },
    )
    project.route_2d["rotation"] = map_rotation
    project.model_3d.route_width_mm = route_width
    project.model_3d.route_height_mm = route_height
    project.model_3d.terrain_height_mm = terrain_height
    project.model_3d.terrain_route_style = "inlay" if support_free_inlay else "tube"
    project.model_3d.inlay_clearance_mm = inlay_clearance
    if photo_upload:
        photo_path = work / photo_upload.name
        photo_path.write_bytes(photo_upload.getvalue())
        project.photo.path = str(photo_path)
    if dem_upload:
        dem_path = work / dem_upload.name
        dem_path.write_bytes(dem_upload.getvalue())
        project.model_3d.dem_path = str(dem_path)
        project.model_3d.mode = "terrain"

    preview_column, details_column = st.columns([1.8, 1], gap="large")
    with preview_column:
        frame_tab, mounted_tab, print_tab = st.tabs(
            ["Quadro", "Detalhe 3D", "Arquivo de impressão"]
        )
        template = load_template(template_name)
        with frame_tab:
            st.image(
                render_framed_preview(activity, project, template),
                use_container_width=True,
            )
        with mounted_tab:
            st.image(
                render_mounted_preview(activity, project, template, dpi=140),
                use_container_width=True,
            )
        with print_tab:
            st.image(render_image(activity, project, template, dpi=140), use_container_width=True)
    with details_column:
        st.subheader("Atividade")
        metric_a, metric_b = st.columns(2)
        metric_a.metric("Distância", f"{activity.metrics.distance_m / 1000:.2f} km")
        metric_b.metric("Ganho", f"{activity.metrics.elevation_gain_m or 0:.0f} m")
        st.caption(f"{len(activity.points):,} pontos válidos no GPX")
        if dem_upload:
            st.success("Terrain ativo: o relevo real será usado nos arquivos STL.")
        else:
            st.warning("Sem DEM: a prévia mostra material estilizado e o STL usa base plana.")
        st.divider()
        if st.button("Gerar pacote completo", type="primary", use_container_width=True):
            try:
                files = export_all(activity, project, Path("output"), "activity")
            except (RuntimeError, ValueError) as error:
                logger.exception("Falha ao gerar o pacote de exportacao")
                st.error(f"Não foi possível gerar os arquivos: {error}")
            else:
                st.success("Arquivos gerados em output/")
                st.json({key: str(value) for key, value in files.items()})
