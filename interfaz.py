import streamlit as st
from Core.gee_init import inicializar_gee, obtener_zona_estudio

<<<<<<< HEAD
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
# FUNCIÓN DE GRÁFICO
# ===============================
def grafico_rango_anios(serie, anios_seleccionados, titulo):

    anio_inicio = min(anios_seleccionados)
    anio_fin = max(anios_seleccionados)

    anios = []
    valores = []

    for d in serie:
        if (
            d["Valor"] is not None
            and anio_inicio <= d["Año"] <= anio_fin
        ):
            anios.append(d["Año"])
            valores.append(d["Valor"])

    if valores:
        st.subheader(titulo)
        st.line_chart(
            {str(a): v for a, v in zip(anios, valores)}
        )
    else:
        st.warning("No hay datos suficientes para generar el gráfico.")

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
    serie = serie_temporal(indice)

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
    anios_sel = [anios[0], anios[1], anios[2]]

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

    st.divider()
    grafico_rango_anios(
        serie,
        anios_sel,
        f"Evolución temporal del {indice} (rango seleccionado)"
    )

# ===============================
# TAB 2 – GRÁFICO TEMPORAL
# ===============================
with tab_grafico:
    serie = serie_temporal(indice)
    # ===========================
    # GRÁFICO 1 – SERIE TEMPORAL
    # ===========================
    grafico_rango_anios(
        serie,
        [2000, 2025],  # rango completo
        f"Evolución temporal del {indice}"
    )
    st.divider()

    # ===========================
    # GRÁFICO 2 – BOXPLOT
    # ===========================
    anios = []
    valores = []

    for d in serie:
        if d["Valor"] is not None:
            anios.append(d["Año"])
            valores.append(d["Valor"])

    st.subheader("Distribución del índice por periodos")
=======
st.set_page_config(
    page_title="Sistema de Análisis Landsat – Río Chili",
    layout="wide",
)

# Inicializar GEE primero
try:
    inicializar_gee()
except Exception as e:
    st.error(f"Error al inicializar Google Earth Engine: {str(e)}")
    st.info("Por favor, verifica tus credenciales de GEE en las variables de entorno.")
    st.stop()

# Luego obtener la zona de estudio
if "zona_estudio" not in st.session_state:
    try:
        st.session_state["zona_estudio"] = obtener_zona_estudio()
    except Exception as e:
        st.error(f"Error al cargar la zona de estudio: {str(e)}")
        st.info("Verifica que el asset 'projects/fourth-return-458106-r5/assets/uchumayo' exista y sea accesible.")
        st.stop()

# ===============================
# PÁGINA DE INICIO
# ===============================
st.title("Sistema de Análisis Landsat – Río Chili")

st.markdown("""
## Bienvenido al Sistema de Análisis Multitemporal
>>>>>>> a7b0fbbed3baef3716983e636d9d130e197ddf66

Este sistema permite analizar índices espectrales derivados de imágenes Landsat 
para la cuenca del Río Chili, Arequipa.

### Funcionalidades disponibles:

**Exploración Espacial**
- Visualiza índices espectrales de un año específico
- Explora diferentes índices de vegetación y agua
- Ajusta la opacidad de las capas

**Análisis Multitemporal**
- Compara 3 años diferentes simultáneamente
- Visualiza series temporales (2000-2025)
- Analiza anomalías y tendencias
- Estadísticas por periodo

###Índices disponibles:
- **NDVI** - Índice de Vegetación Normalizado
- **SAVI** - Índice de Vegetación Ajustado al Suelo
- **EVI** - Índice de Vegetación Mejorado
- **GNDVI** - Índice Verde Normalizado
- **LSWI** - Índice de Agua en Onda Corta
- **NDWI** - Índice de Agua Normalizado
- **MNDWI** - Índice de Agua Modificado

---
""")

col1, col2 = st.columns(2)

with col1:
    st.info("Zona de estudio cargada correctamente")
    st.info("**Área de estudio:** Cuenca Río Chili, Uchumayo")

with col2:
    st.info("**Período disponible:** 2000 - 2025")
    st.info("**Satélites:** Landsat 7 (2000-2011) y Landsat 8 (2012-2025)")
