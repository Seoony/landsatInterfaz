import ee
import streamlit as st
import folium
from streamlit_folium import st_folium
import os

# INICIALIZACIÓN GOOGLE EARTH ENGINE
# Try to initialize with service account if available, otherwise use default credentials
try:
    service_account_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
    if service_account_path and os.path.exists(service_account_path):
        credentials = ee.ServiceAccountCredentials(None, service_account_path)
        ee.Initialize(credentials, project='fourth-return-458106-r5')
    else:
        ee.Initialize(project='fourth-return-458106-r5')
except Exception as e:
    st.error(f"Error initializing Google Earth Engine: {e}")
    st.stop()

# ZONA DE ESTUDIO (ASSET)
zona_estudio = ee.FeatureCollection(
    "projects/fourth-return-458106-r5/assets/uchumayo"
).geometry()


# FUNCIÓN PARA OBTENER ÍNDICES
def obtener_indice(anio, semestre, indice):
    mes_inicio = 1 if semestre == 1 else 7
    mes_fin = 6 if semestre == 1 else 12

    fecha_inicio = ee.Date.fromYMD(anio, mes_inicio, 1)
    fecha_fin = ee.Date.fromYMD(anio, mes_fin, 28)

    coleccion = ee.ImageCollection(
        'LANDSAT/LT05/C02/T1_L2' if anio <= 2011
        else 'LANDSAT/LC08/C02/T1_L2'
    )

    imagen = (
        coleccion
        .filterDate(fecha_inicio, fecha_fin)
        .filterBounds(zona_estudio)
        .filter(ee.Filter.lt('CLOUD_COVER', 20))
        .median()
    )

    bandas_l5 = ['SR_B1', 'SR_B2', 'SR_B3', 'SR_B4', 'SR_B5', 'SR_B7']
    bandas_l8 = ['SR_B2', 'SR_B3', 'SR_B4', 'SR_B5', 'SR_B6', 'SR_B7']
    bandas_std = ['BLUE', 'GREEN', 'RED', 'NIR', 'SWIR1', 'SWIR2']

    bandas_origen = ee.List(
        ee.Algorithms.If(anio <= 2011, bandas_l5, bandas_l8)
    )

    imagen = imagen.select(bandas_origen).rename(bandas_std)

    if indice == 'NDVI':
        img = imagen.normalizedDifference(['NIR', 'RED'])
    elif indice == 'SAVI':
        img = imagen.expression(
            '(NIR - RED) / (NIR + RED + 0.5) * 1.5',
            {'NIR': imagen.select('NIR'), 'RED': imagen.select('RED')}
        )
    elif indice == 'EVI':
        img = imagen.expression(
            '2.5 * ((NIR - RED) / (NIR + 6 * RED - 7.5 * BLUE + 1))',
            {
                'NIR': imagen.select('NIR'),
                'RED': imagen.select('RED'),
                'BLUE': imagen.select('BLUE')
            }
        )
    elif indice == 'GNDVI':
        img = imagen.normalizedDifference(['NIR', 'GREEN'])
    elif indice == 'LSWI':
        img = imagen.normalizedDifference(['NIR', 'SWIR1'])
    elif indice == 'NDWI':
        img = imagen.normalizedDifference(['GREEN', 'NIR'])
    elif indice == 'MNDWI':
        img = imagen.normalizedDifference(['GREEN', 'SWIR1'])
    else:
        img = imagen.normalizedDifference(['NIR', 'RED'])

    return img.rename(indice).clip(zona_estudio)

# INTERFAZ STREAMLIT
st.set_page_config(layout="wide")
st.title("Visualizador de Índices Landsat – Río Chili")

with st.sidebar:
    st.header("Parámetros")
    indice = st.selectbox(
        "Índice espectral",
        ['NDVI', 'SAVI', 'EVI', 'GNDVI', 'LSWI', 'NDWI', 'MNDWI']
    )
    anio = st.slider("Año", 2000, 2025, 2023)
    semestre = st.selectbox("Semestre", [1, 2])

# PROCESAMIENTO
imagen_indice = obtener_indice(anio, semestre, indice)


# MAPA
mapa = folium.Map(
    location=[-16.42, -71.54],
    zoom_start=12,
    tiles="OpenStreetMap"
)

vis_params = {
    "NDVI": {"min": -0.2, "max": 0.9, "palette": ["brown", "yellow", "green"]},
    "SAVI": {"min": -0.2, "max": 0.9, "palette": ["brown", "yellow", "green"]},
    "EVI":  {"min": -0.2, "max": 0.9, "palette": ["brown", "yellow", "green"]},
    "GNDVI":{"min": -0.2, "max": 0.9, "palette": ["brown", "yellow", "green"]},
    "LSWI": {"min": -0.5, "max": 0.8, "palette": ["brown", "white", "blue"]},
    "NDWI": {"min": -0.5, "max": 0.8, "palette": ["white", "cyan", "blue"]},
    "MNDWI":{"min": -0.5, "max": 0.8, "palette": ["white", "lightblue", "darkblue"]}
}

tiles = imagen_indice.getMapId(vis_params[indice])

folium.TileLayer(
    tiles=tiles["tile_fetcher"].url_format,
    attr="Google Earth Engine",
    name=indice,
    overlay=True
).add_to(mapa)

folium.LayerControl().add_to(mapa)

st_folium(mapa, width=1400, height=500)
