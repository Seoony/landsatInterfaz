import ee
import streamlit as st
import folium
from streamlit_folium import st_folium
import os
import json

# ===============================
# INICIALIZACIÓN GOOGLE EARTH ENGINE
# ===============================
try:
    client_id = os.getenv('EE_CLIENT_ID') or os.getenv('CLIENT_ID')
    client_secret = os.getenv('EE_CLIENT_SECRET') or os.getenv('CLIENT_SECRET')
    refresh_token = os.getenv('EE_REFRESH_TOKEN') or os.getenv('REFRESH_TOKEN')

    if client_id and client_secret and refresh_token:
        oauth_credentials = {
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
            "type": "authorized_user"
        }
        credentials_dir = os.path.join(
            os.path.expanduser('~'), '.config', 'earthengine'
        )
        os.makedirs(credentials_dir, exist_ok=True)
        with open(os.path.join(credentials_dir, 'credentials'), 'w') as f:
            json.dump(oauth_credentials, f)

    ee.Initialize(project='fourth-return-458106-r5')

except Exception as e:
    st.error(f"Error initializing Google Earth Engine: {e}")
    st.stop()

# ===============================
# ZONA DE ESTUDIO
# ===============================
zona_estudio = ee.FeatureCollection(
    "projects/fourth-return-458106-r5/assets/uchumayo"
).geometry()

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

# ===============================
# OBTENER IMAGEN (CACHEADA)
# ===============================
@st.cache_data(show_spinner=False)
def obtener_indice(anio, indice):
    fecha_inicio = ee.Date.fromYMD(anio, 1, 1)
    fecha_fin = ee.Date.fromYMD(anio, 12, 31)

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

    img_indice = INDICES[indice](imagen)

    return img_indice.rename(indice).clip(zona_estudio)

# ===============================
# ESTADÍSTICAS (CACHEADAS)
# ===============================
@st.cache_data(show_spinner=False)
def estadisticas_indice(anio, indice):
    img = obtener_indice(anio, indice)
    stats = img.reduceRegion(
        reducer=ee.Reducer.mean()
            .combine(ee.Reducer.min(), '', True)
            .combine(ee.Reducer.max(), '', True),
        geometry=zona_estudio,
        scale=30,
        maxPixels=1e9
    )
    return stats.getInfo()

# ===============================
# INTERFAZ STREAMLIT
# ===============================
st.set_page_config(layout="wide")
st.title("Comparación de Índices Landsat – Río Chili")

with st.sidebar:
    indice = st.selectbox(
        "Índice espectral",
        list(INDICES.keys())
    )

    anios = [
        st.selectbox("Año 1", range(2000, 2026), index=23),
        st.selectbox("Año 2", range(2000, 2026), index=20),
        st.selectbox("Año 3", range(2000, 2026), index=17)
    ]

    opacity = st.slider("Opacidad", 0.0, 1.0, 0.6, 0.1)

# ===============================
# VISUALIZACIÓN
# ===============================
columnas = st.columns(3)

vis_params = {
    "NDVI": {"min": -0.2, "max": 0.9, "palette": ["brown", "yellow", "green"]},
    "SAVI": {"min": -0.2, "max": 0.9, "palette": ["brown", "yellow", "green"]},
    "EVI":  {"min": -0.2, "max": 0.9, "palette": ["brown", "yellow", "green"]},
    "GNDVI":{"min": -0.2, "max": 0.9, "palette": ["brown", "yellow", "green"]},
    "LSWI": {"min": -0.5, "max": 0.8, "palette": ["brown", "white", "blue"]},
    "NDWI": {"min": -0.5, "max": 0.8, "palette": ["white", "cyan", "blue"]},
    "MNDWI":{"min": -0.5, "max": 0.8, "palette": ["white", "lightblue", "darkblue"]}
}

for col, anio in zip(columnas, anios):
    with col:
        st.subheader(f"{indice} – {anio}")

        imagen = obtener_indice(anio, indice)
        tiles = imagen.getMapId(vis_params[indice])

        mapa = folium.Map(
            location=[-16.42, -71.54],
            zoom_start=11,
            tiles="OpenStreetMap"
        )

        folium.TileLayer(
            tiles=tiles["tile_fetcher"].url_format,
            attr="Google Earth Engine",
            overlay=True,
            opacity=opacity
        ).add_to(mapa)

        st_folium(
            mapa,
            width=450,
            height=380,
            key=f"mapa_{indice}_{anio}"
        )

        stats = estadisticas_indice(anio, indice)

        st.markdown(
            f"""
            **{indice} promedio:** {stats[indice + '_mean']:.3f}  
            **Valor mínimo:** {stats[indice + '_min']:.3f}  
            **Valor máximo:** {stats[indice + '_max']:.3f}
            """
        )
