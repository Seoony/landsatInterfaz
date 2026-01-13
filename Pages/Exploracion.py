import streamlit as st
import folium
from streamlit_folium import st_folium
import ee
from Core.gee_init import asegurar_zona_estudio

# ===============================
# INICIALIZACIÓN Y CONTEXTO
# ===============================
zona_estudio = asegurar_zona_estudio()

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
        coleccion = ee.ImageCollection('LANDSAT/LE07/C02/T1_L2')
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

# ===============================
# INTERFAZ
# ===============================
st.title("Exploración Espacial – Índice Espectral")

with st.sidebar:
    indice = st.selectbox("Índice espectral", list(INDICES.keys()))
    anio = st.selectbox("Año", range(2000, 2026), index=23)
    opacidad = st.slider("Opacidad", 0.0, 1.0, 0.7, 0.1)

    imagen = obtener_imagen(anio, indice, zona_estudio)
    tiles = imagen.getMapId(VIS_PARAMS[indice])

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


st_folium(mapa, width=1200, height=650, key=f"mapa_{indice}_{anio}_{opacidad}")
