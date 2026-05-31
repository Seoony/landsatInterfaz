import base64
from pathlib import Path
 
import ee
import folium
import streamlit as st
from streamlit_folium import st_folium
 
from Core.datos import cargar_tabla_muestreo, obtener_indice
from Core.gee_init import asegurar_zona_estudio
from Core.indices import INDICES, VIS_PARAMS
 
# ── Contexto ─────────────────────────────────────────────────────────────────
zona_estudio = asegurar_zona_estudio()
 
# ── Puntos de muestreo ───────────────────────────────────────────────────────
PUNTOS = ee.FeatureCollection([
    ee.Feature(ee.Geometry.Point([-71.5982778, -16.4557667]), {"nombre": "Punto 1"}),
    ee.Feature(ee.Geometry.Point([-71.5979417, -16.4553806]), {"nombre": "Punto 2"}),
    ee.Feature(ee.Geometry.Point([-71.6313639, -16.4287806]), {"nombre": "Punto 3"}),
])
 
 
# ── Utilidades ───────────────────────────────────────────────────────────────
 
def imagen_a_base64(ruta: str):
    p = Path(ruta)
    if not p.exists():
        return None
    with open(p, "rb") as f:
        return base64.b64encode(f.read()).decode()
 
 
def agregar_puntos_muestreo(mapa, puntos, tabla_df):
    for feature in puntos.getInfo()["features"]:
        coords  = feature["geometry"]["coordinates"]
        nombre  = feature["properties"].get("nombre", "Punto")
        clave   = nombre.replace("Punto ", "P")
 
        datos_punto = tabla_df[tabla_df["Punto"] == clave]
        tabla_html  = (
            datos_punto.to_html(index=False, classes="table table-striped table-sm", border=0)
            if not datos_punto.empty
            else "<i>No hay datos disponibles</i>"
        )
 
        img_b64  = imagen_a_base64(f"Imagenes/{clave}.jpg")
        img_html = (
            f'<img src="data:image/jpeg;base64,{img_b64}" '
            f'style="width:100%;margin-bottom:8px;border-radius:6px;">'
            if img_b64 else "<i>Imagen no disponible</i><br>"
        )
 
        popup_html = f"""
        <div style="width:500px">
            <b>{nombre}</b><br>
            <b>Coordenadas:</b><br>
            Lat: {coords[1]:.6f}<br>
            Lon: {coords[0]:.6f}<br><br>
            {img_html}
            <b>Datos recolectados:</b>
            {tabla_html}
        </div>
        """
        folium.Marker(
            location=[coords[1], coords[0]],
            popup=folium.Popup(popup_html, max_width=500),
            icon=folium.Icon(color="red", icon="info-sign"),
        ).add_to(mapa)
 
 
# ── Interfaz ─────────────────────────────────────────────────────────────────
st.title("Exploración Espacial – Índice Espectral")
 
with st.sidebar:
    indice   = st.selectbox("Índice espectral", list(INDICES.keys()))
    anio     = st.selectbox("Año", range(2000, 2026), index=23)
    opacidad = st.slider("Opacidad", 0.0, 1.0, 0.7, 0.1)
 
    if st.button("Actualizar datos"):
        st.cache_data.clear()
 
# Carga de datos 
tabla_puntos = cargar_tabla_muestreo()
imagen       = obtener_indice(anio, indice)
tiles        = imagen.getMapId(VIS_PARAMS[indice])
 
# ── Mapa ─────────────────────────────────────────────────────────────────────
mapa = folium.Map(location=[-16.42, -71.54], zoom_start=11, tiles="OpenStreetMap")
 
folium.TileLayer(
    tiles=tiles["tile_fetcher"].url_format,
    attr="Google Earth Engine",
    overlay=True,
    opacity=opacidad,
).add_to(mapa)
 
agregar_puntos_muestreo(mapa, PUNTOS, tabla_puntos)
 
st_folium(mapa, width="100%", height=700, key=f"mapa_{indice}_{anio}_{opacidad}")