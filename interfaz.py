import ee
import streamlit as st
import folium
from streamlit_folium import st_folium
import os
import json
import plotly.graph_objects as go

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
# OBTENER IMAGEN
# ===============================
@st.cache_data(show_spinner=False)
def obtener_indice(anio, indice):
    fecha_inicio = ee.Date.fromYMD(anio, 1, 1)
    fecha_fin = ee.Date.fromYMD(anio, 12, 31)

    if anio <= 2011:
        coleccion = ee.ImageCollection('LANDSAT/LE07/C02/T1_L2')
        bandas_origen = ['SR_B1', 'SR_B2', 'SR_B3', 'SR_B4', 'SR_B5', 'SR_B7']
    else:
        coleccion = ee.ImageCollection('LANDSAT/LC08/C02/T1_L2')
        bandas_origen = ['SR_B2', 'SR_B3', 'SR_B4', 'SR_B5', 'SR_B6', 'SR_B7']

    imagen = (
        coleccion
        .filterDate(fecha_inicio, fecha_fin)
        .filterBounds(zona_estudio)
        .filter(ee.Filter.lt('CLOUD_COVER', 20))
        .median()
    )

    bandas_std = ['BLUE', 'GREEN', 'RED', 'NIR', 'SWIR1', 'SWIR2']
    imagen = imagen.select(bandas_origen).rename(bandas_std)

    img_indice = INDICES[indice](imagen).rename(indice)

    return img_indice.clip(zona_estudio)


# ===============================
# ESTADÍSTICAS
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
# SERIE TEMPORAL
# ===============================
@st.cache_data(show_spinner=False)
def serie_temporal(indice, anio_inicio=2000, anio_fin=2025):

    def calcular_valor(anio):
        anio = ee.Number(anio)
        fecha_inicio = ee.Date.fromYMD(anio, 1, 1)
        fecha_fin = ee.Date.fromYMD(anio, 12, 31)

        coleccion = ee.ImageCollection(
            ee.Algorithms.If(
                anio.lte(2011),
                ee.ImageCollection('LANDSAT/LE07/C02/T1_L2'),
                ee.ImageCollection('LANDSAT/LC08/C02/T1_L2')
            )
        )

        coleccion = (
            coleccion
            .filterDate(fecha_inicio, fecha_fin)
            .filterBounds(zona_estudio)
            .filter(ee.Filter.lt('CLOUD_COVER', 20))
        )

        size = coleccion.size()

        def calcular_indice():
            imagen = coleccion.median()

            bandas_origen = ee.List(
                ee.Algorithms.If(
                    anio.lte(2011),
                    ['SR_B1','SR_B2','SR_B3','SR_B4','SR_B5','SR_B7'],
                    ['SR_B2','SR_B3','SR_B4','SR_B5','SR_B6','SR_B7']
                )
            )

            bandas_std = ['BLUE','GREEN','RED','NIR','SWIR1','SWIR2']
            imagen = imagen.select(bandas_origen).rename(bandas_std)

            img_indice = INDICES[indice](imagen).rename(indice)

            reduccion = img_indice.reduceRegion(
                reducer=ee.Reducer.mean(),
                geometry=zona_estudio,
                scale=30,
                maxPixels=1e9
            )

            return ee.Algorithms.If(
                reduccion.contains(indice),
                reduccion.get(indice),
                None
            )

        valor = ee.Algorithms.If(
            size.gt(0),
            calcular_indice(),
            None
        )

        return ee.Feature(None, {
            'Año': anio,
            'Valor': valor
        })

    fc = ee.FeatureCollection(
        ee.List.sequence(anio_inicio, anio_fin).map(calcular_valor)
    )

    datos = fc.getInfo()

    serie = []
    for f in datos['features']:
        props = f['properties']
        serie.append({
            "Año": int(props['Año']),
            "Valor": props.get('Valor')
        })

    return serie


# ===============================
# INTERFAZ STREAMLIT
# ===============================
st.set_page_config(layout="wide")
st.title("Comparación de Índices Landsat – Río Chili")

with st.sidebar:
    indice = st.selectbox("Índice espectral", list(INDICES.keys()))

    anios = [
        st.selectbox("Año 1", range(2000, 2026), index=23),
        st.selectbox("Año 2", range(2000, 2026), index=20),
        st.selectbox("Año 3", range(2000, 2026), index=17)
    ]

    opacity = st.slider("Opacidad", 0.0, 1.0, 0.6, 0.1)

# ===============================
# PESTAÑAS
# ===============================
tab_mapas, tab_grafico = st.tabs(
    ["Mapas y estadísticas", "Gráficos Analíticos"]
)

# ===============================
# TAB 1 – MAPAS Y ESTADÍSTICAS
# ===============================
with tab_mapas:
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

    for i, (col, anio) in enumerate(zip(columnas, anios)):
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
                key=f"mapa_{indice}_{anio}_{i}"
            )
            stats = estadisticas_indice(anio, indice)

            st.markdown(
                f"""
                **{indice} promedio:** {stats[indice + '_mean']:.3f}  
                **Valor mínimo:** {stats[indice + '_min']:.3f}  
                **Valor máximo:** {stats[indice + '_max']:.3f}
                """
            )

# ===============================
# TAB 2 – GRÁFICO TEMPORAL
# ===============================
with tab_grafico:
    st.subheader(f"Evolución temporal del {indice}")

    serie = serie_temporal(indice)

    # ===========================
    # GRÁFICO 1 – SERIE TEMPORAL
    # ===========================
    anios = []
    valores = []

    for d in serie:
        if d["Valor"] is not None:
            anios.append(d["Año"])
            valores.append(d["Valor"])

    if valores:
        st.line_chart(
            {str(a): v for a, v in zip(anios, valores)}
        )
    else:
        st.warning("No hay datos suficientes para generar el gráfico.")
        st.stop()

    st.divider()

    # ===========================
    # GRÁFICO 2 – BOXPLOT
    # ===========================
    st.subheader("Distribución del índice por periodos")

    periodo1 = [v for a, v in zip(anios, valores) if 2000 <= a <= 2006]
    periodo2 = [v for a, v in zip(anios, valores) if 2007 <= a <= 2012]
    periodo3 = [v for a, v in zip(anios, valores) if 2013 <= a <= 2025]

    fig_box = go.Figure()

    if periodo1:
        fig_box.add_trace(go.Box(y=periodo1, name="2000–2006", marker_color="red"))
    if periodo2:
        fig_box.add_trace(go.Box(y=periodo2, name="2007–2012", marker_color="orange"))
    if periodo3:
        fig_box.add_trace(go.Box(y=periodo3, name="2013–2025", marker_color="green"))

    fig_box.update_layout(
        yaxis_title=indice,
        boxmode="group"
    )

    st.plotly_chart(fig_box, use_container_width=True)

    st.divider()

    # ===========================
    # GRÁFICO 3 – ANOMALÍAS
    # ===========================
    st.subheader("Análisis de anomalías")

    valores = [
        d["Valor"] for d in serie if d["Valor"] is not None
    ]
    anios_validos = [
        d["Año"] for d in serie if d["Valor"] is not None
    ]
    media = sum(valores) / len(valores)

    # Desviación estándar
    varianza = sum((v - media) ** 2 for v in valores) / len(valores)
    std = varianza ** 0.5

    anomalias = [v - media for v in valores]

    # ===============================
    # Clasificación por severidad
    # ===============================
    colores = []

    for a in anomalias:
        if abs(a) >= std:
            colores.append("darkgreen" if a > 0 else "darkred")
        elif abs(a) >= 0.5 * std:
            colores.append("green" if a > 0 else "red")
        else:
            colores.append("lightgreen" if a > 0 else "lightcoral")

    # ===============================
    # Gráfico de anomalías
    # ===============================
    fig_anom = go.Figure()

    fig_anom.add_trace(go.Bar(
        x=anios_validos,
        y=anomalias,
        marker_color=colores,
        name="Anomalía"
    ))

    fig_anom.add_hline(
        y=0,
        line_width=2,
        line_color="black"
    )

    fig_anom.update_layout(
        title=f"Anomalías del {indice} respecto al promedio histórico",
        xaxis_title="Año",
        yaxis_title="Anomalía",
        showlegend=False
    )

    st.plotly_chart(fig_anom, use_container_width=True)

    # ===============================
    # Mostrar valores estadísticos
    # ===============================
    st.markdown(
        f"""
        **Promedio histórico:** {media:.4f}  
        **Desviación estándar:** {std:.4f}
        """
    )