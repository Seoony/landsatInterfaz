import streamlit as st
import folium
from streamlit_folium import st_folium
import ee
import pandas as pd
import base64
from pathlib import Path
from Core.gee_init import asegurar_zona_estudio

# ===============================
# INICIALIZACIÓN Y CONTEXTO
# ===============================
zona_estudio = asegurar_zona_estudio()

# =========================
# PUNTOS DE MUESTREO
# =========================
puntos = ee.FeatureCollection([
    ee.Feature(ee.Geometry.Point([-71.5982778, -16.4557667]), {'nombre': 'Punto 1'}),
    ee.Feature(ee.Geometry.Point([-71.5979417, -16.4553806]), {'nombre': 'Punto 2'}),
    ee.Feature(ee.Geometry.Point([-71.6313639, -16.4287806]), {'nombre': 'Punto 3'})
])


# ===============================
# CARGA DE TABLA GOOGLE SHEETS
# ===============================
@st.cache_data(ttl=300, show_spinner=False)
def cargar_tabla_sheets_xlsx(url):
    df = pd.read_excel(url)

    df = df.rename(columns={
        df.columns[0]: "Punto",
        df.columns[1]: "Profundidad",
        df.columns[2]: "Fertilidad",
        df.columns[3]: "pH",
        df.columns[4]: "Humedad",
        df.columns[5]: "Temperatura"
    })

    # 1. Rellenar Punto hacia abajo (P1 → fila de 14 cm)
    df["Punto"] = df["Punto"].ffill()

    # 2. Eliminar filas sin profundidad
    df = df.dropna(subset=["Profundidad"])

    # 3. Mantener SOLO 2 registros por punto (0 y 14 cm)
    df = (
        df.groupby("Punto", as_index=False)
        .head(2)
        .reset_index(drop=True)
    )

    return df

URL_SHEETS = "https://docs.google.com/spreadsheets/d/1yQ3TJRpGAGqSnSfGgQP4c9UwwDt-RZwS/export?format=xlsx"
tabla_puntos = cargar_tabla_sheets_xlsx(URL_SHEETS)

def imagen_a_base64(ruta):
    ruta = Path(ruta)
    if not ruta.exists():
        return None
    with open(ruta, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")
    
# ===============================
# DEFINICIÓN DE ÍNDICES
# ===============================
INDICES = {
    "NDVI": lambda img: img.normalizedDifference(['NIR', 'RED']),
    "SAVI": lambda img: img.expression(
        '(NIR - RED) / (NIR + RED + 0.5) * 1.5',
        {'NIR': img.select('NIR'), 'RED': img.select('RED')}
    ),
    "EVI": lambda img: img.expression(
        '2.5 * ((NIR - RED) / (NIR + 6 * RED - 7.5 * BLUE + 1))',
        {
            'NIR': img.select('NIR'),
            'RED': img.select('RED'),
            'BLUE': img.select('BLUE')
        }
    ),
    "GNDVI": lambda img: img.normalizedDifference(['NIR', 'GREEN']),
    "LSWI": lambda img: img.normalizedDifference(['NIR', 'SWIR1']),
    "NDWI": lambda img: img.normalizedDifference(['GREEN', 'NIR']),
    "MNDWI": lambda img: img.normalizedDifference(['GREEN', 'SWIR1'])
}

VIS_PARAMS = {
    "NDVI": {"min": -0.2, "max": 0.9, "palette": ["brown", "yellow", "green"]},
    "SAVI": {"min": -0.2, "max": 0.9, "palette": ["brown", "yellow", "green"]},
    "EVI":  {"min": -0.2, "max": 0.9, "palette": ["brown", "yellow", "green"]},
    "GNDVI":{"min": -0.2, "max": 0.9, "palette": ["brown", "yellow", "green"]},
    "LSWI": {"min": -0.5, "max": 0.8, "palette": ["brown", "white", "blue"]},
    "NDWI": {"min": -0.5, "max": 0.8, "palette": ["white", "cyan", "blue"]},
    "MNDWI":{"min": -0.5, "max": 0.8, "palette": ["white", "lightblue", "darkblue"]}
}

# ===============================
# FUNCIONES
# ===============================
@st.cache_data(show_spinner=False)
def obtener_imagen(anio, indice, _zona_estudio):
    fecha_inicio = ee.Date.fromYMD(anio, 1, 1)
    fecha_fin = ee.Date.fromYMD(anio, 12, 31)

    if anio <= 2011:
        coleccion = ee.ImageCollection('LANDSAT/LE05/C02/T1_L2')
        bandas = ['SR_B1','SR_B2','SR_B3','SR_B4','SR_B5','SR_B7']
    elif anio == 2012:
        coleccion5 = ee.ImageCollection('LANDSAT/LT05/C02/T1_L2')
        coleccion7 = ee.ImageCollection('LANDSAT/LE07/C02/T1_L2')
        coleccion = coleccion5.merge(coleccion7)
        bandas = ['SR_B1','SR_B2','SR_B3','SR_B4','SR_B5','SR_B7']
    else:
        coleccion = ee.ImageCollection('LANDSAT/LC08/C02/T1_L2')
        bandas = ['SR_B2','SR_B3','SR_B4','SR_B5','SR_B6','SR_B7']

    imagen = (
        coleccion
        .filterDate(fecha_inicio, fecha_fin)
        .filterBounds(_zona_estudio)
        .filter(ee.Filter.lt('CLOUD_COVER', 20))
        .median()
        .select(bandas)
        .rename(['BLUE','GREEN','RED','NIR','SWIR1','SWIR2'])
    )

    return INDICES[indice](imagen).rename(indice).clip(_zona_estudio)

def generar_tabla_popup(df, punto):
    datos = df[df["Punto"] == punto]

    if datos.empty:
        return "<i>No hay datos disponibles</i>"

    tabla_html = datos[[
        "Profundidad",
        "Fertilidad",
        "pH",
        "Humedad",
        "Temperatura"
    ]].to_html(
        index=False,
        classes="table table-striped table-sm",
        border=0
    )

    return tabla_html

def agregar_puntos_muestreo(mapa, puntos, tabla_df):
    puntos_geojson = puntos.getInfo()

    for f in puntos_geojson["features"]:
        coords = f["geometry"]["coordinates"]
        nombre = f["properties"].get("nombre", "Punto")

        clave_punto = nombre.replace("Punto ", "P")

        datos_punto = tabla_df[tabla_df["Punto"] == clave_punto]

        if not datos_punto.empty:
            tabla_html = datos_punto.to_html(
                index=False,
                classes="table table-striped table-sm",
                border=0
            )
        else:
            tabla_html = "<i>No hay datos disponibles</i>"
        
        ruta_img = f"Imagenes/{clave_punto}.jpg"
        img_base64 = imagen_a_base64(ruta_img)

        if img_base64:
            img_html = f"""
            <img src="data:image/jpeg;base64,{img_base64}"
                 style="width:100%; margin-bottom:8px; border-radius:6px;">
            """
        else:
            img_html = "<i>Imagen no disponible</i><br>"


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
            icon=folium.Icon(color="red", icon="info-sign")
        ).add_to(mapa)



# ===============================
# INTERFAZ
# ===============================
st.title("Exploración Espacial – Índice Espectral")

with st.sidebar:
    indice = st.selectbox("Índice espectral", list(INDICES.keys()))
    anio = st.selectbox("Año", range(2000, 2026), index=23)
    opacidad = st.slider("Opacidad", 0.0, 1.0, 0.7, 0.1)

    # Botón para forzar actualización de datos
    if st.button("Actualizar datos"):
        st.cache_data.clear()

    imagen = obtener_imagen(anio, indice, zona_estudio)
    tiles = imagen.getMapId(VIS_PARAMS[indice])

# ===============================
# CARGA DE TABLA DE GOOGLE SHEETS (TEMPORAL)
# ===============================
#tabla_puntos = cargar_tabla_sheets_xlsx(URL_SHEETS)

#st.subheader("Tabla de datos de puntos de muestreo (verificación)")
#st.dataframe(tabla_puntos)
# ===============================

mapa = folium.Map(
    location=[-16.42, -71.54],
    zoom_start=11,
    tiles="OpenStreetMap"
)

folium.TileLayer(
    tiles=tiles["tile_fetcher"].url_format,
    attr="Google Earth Engine",
    overlay=True,
    opacity=opacidad
).add_to(mapa)

agregar_puntos_muestreo(mapa, puntos, tabla_puntos)

st_folium(
    mapa,
    width="100%",
    height=700,
    key=f"mapa_{indice}_{anio}_{opacidad}"
)
