"""Local Streamlit editor for GPX poster projects."""

from __future__ import annotations

import tempfile
from pathlib import Path

import streamlit as st

from strava_print.domain.models import Project
from strava_print.export.package import export_all
from strava_print.gpx.parser import GPXError, parse_gpx
from strava_print.layouts.templates import available_templates, load_template
from strava_print.renderers.raster_renderer import render_image

st.set_page_config(page_title="Strava Print", layout="wide")
st.title("GPX Print Studio")
with st.sidebar:
    gpx_upload = st.file_uploader("Arquivo GPX", type=["gpx"])
    photo_upload = st.file_uploader("Fotografia", type=["jpg", "jpeg", "png", "webp"])
    dem_upload = st.file_uploader("DEM GeoTIFF (opcional, para relevo 3D)", type=["tif", "tiff"])
    template_name = st.selectbox("Layout", available_templates())
    title = st.text_input("Título", "Morning Ride")
    location = st.text_input("Local", "Izumo, Shimane, Japan")
    activity_type = st.selectbox(
        "Atividade", ["cycling", "running", "walking", "hiking", "generic"]
    )
    units = st.radio("Unidades", ["metric", "imperial"], horizontal=True)
    map_rotation = st.slider("Rotação do mapa", -180, 180, 0)
    route_width = st.slider("Largura da rota 3D (mm)", 0.8, 4.0, 1.8, 0.1)
    terrain_height = st.slider("Altura do relevo (mm)", 2.0, 20.0, 8.0, 0.5)
if not gpx_upload:
    st.info("Envie um GPX para começar a pré-visualização.")
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
        location=location,
        activity_type=activity_type,
        units=units,
    )
    project.route_2d["rotation"] = map_rotation
    project.model_3d.route_width_mm = route_width
    project.model_3d.terrain_height_mm = terrain_height
    if photo_upload:
        photo_path = work / photo_upload.name
        photo_path.write_bytes(photo_upload.getvalue())
        project.photo.path = str(photo_path)
    if dem_upload:
        dem_path = work / dem_upload.name
        dem_path.write_bytes(dem_upload.getvalue())
        project.model_3d.dem_path = str(dem_path)
        project.model_3d.mode = "terrain"
    left, right = st.columns([2, 1])
    with left:
        st.image(
            render_image(activity, project, load_template(template_name)),
            caption="Prévia proporcional do layout",
        )
    with right:
        st.subheader("Dados identificados")
        st.write(
            {
                "pontos": len(activity.points),
                "distância_m": round(activity.metrics.distance_m),
                "duração_s": activity.metrics.duration_s,
                "ganho_m": activity.metrics.elevation_gain_m,
            }
        )
        if dem_upload:
            st.caption("Terrain ativo: o STL usará o relevo do GeoTIFF enviado.")
        if st.button("Gerar pacote de exportação"):
            output = Path("output")
            files = export_all(activity, project, output, "activity")
            st.success("Pacote gerado em output/")
            st.json({key: str(value) for key, value in files.items()})
