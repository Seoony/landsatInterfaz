import ee
import streamlit as st
import folium
from streamlit_folium import st_folium
import plotly.graph_objects as go
from Core.gee_init import asegurar_zona_estudio 

# ===============================
# CONTEXTO COMPARTIDO
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
# FUNCIONES BASE
# ===============================
@st.cache_data(show_spinner=False)
def obtener_indice(anio, indice):
    if anio <= 2011:
        coleccion = ee.ImageCollection("LANDSAT/LE07/C02/T1_L2")
        bandas = ["SR_B1","SR_B2","SR_B3","SR_B4","SR_B5","SR_B7"]
    else:
        coleccion = ee.ImageCollection("LANDSAT/LC08/C02/T1_L2")
        bandas = ["SR_B2","SR_B3","SR_B4","SR_B5","SR_B6","SR_B7"]

    img = (
        coleccion
        .filterDate(f"{anio}-01-01", f"{anio}-12-31")
        .filterBounds(zona_estudio)
        .filter(ee.Filter.lt("CLOUD_COVER", 20))
        .median()
        .select(bandas)
        .rename(["BLUE","GREEN","RED","NIR","SWIR1","SWIR2"])
    )

    return INDICES[indice](img).rename(indice).clip(zona_estudio)

@st.cache_data(show_spinner=False)
def estadisticas_indice(anio, indice):
    img = obtener_indice(anio, indice)
    stats = img.reduceRegion(
        reducer=ee.Reducer.mean()
        .combine(ee.Reducer.min(), "", True)
        .combine(ee.Reducer.max(), "", True),
        geometry=zona_estudio,
        scale=30,
        maxPixels=1e9
    )
    return stats.getInfo()

@st.cache_data(show_spinner=False)
def serie_temporal(indice, anio_inicio=2000, anio_fin=2025):

    def calcular(anio):
        anio = ee.Number(anio)

        coleccion = ee.ImageCollection(
            ee.Algorithms.If(
                anio.lte(2011),
                ee.ImageCollection("LANDSAT/LE07/C02/T1_L2"),
                ee.ImageCollection("LANDSAT/LC08/C02/T1_L2")
            )
        ).filterDate(
            ee.Date.fromYMD(anio, 1, 1),
            ee.Date.fromYMD(anio, 12, 31)
        ).filterBounds(zona_estudio).filter(
            ee.Filter.lt("CLOUD_COVER", 20)
        )

        def calc():
            img = coleccion.median()
            bandas = ee.List(
                ee.Algorithms.If(
                    anio.lte(2011),
                    ["SR_B1","SR_B2","SR_B3","SR_B4","SR_B5","SR_B7"],
                    ["SR_B2","SR_B3","SR_B4","SR_B5","SR_B6","SR_B7"]
                )
            )
            img = img.select(bandas).rename(
                ["BLUE","GREEN","RED","NIR","SWIR1","SWIR2"]
            )
            ind = INDICES[indice](img).rename(indice)
            red = ind.reduceRegion(
                ee.Reducer.mean(),
                zona_estudio,
                30,
                maxPixels=1e9
            )
            return ee.Algorithms.If(red.contains(indice), red.get(indice), None)

        return ee.Feature(
            None,
            {
                "Año": anio,
                "Valor": ee.Algorithms.If(coleccion.size().gt(0), calc(), None)
            }
        )

    fc = ee.FeatureCollection(
        ee.List.sequence(anio_inicio, anio_fin).map(calcular)
    )

    datos = fc.getInfo()
    return [
        {"Año": int(f["properties"]["Año"]), "Valor": f["properties"].get("Valor")}
        for f in datos["features"]
    ]

# ===============================
# INTERFAZ
# ===============================
st.set_page_config(layout="wide")
st.title("Análisis Multitemporal – Índices Landsat")

with st.sidebar:
    indice = st.selectbox("Índice espectral", list(INDICES.keys()))
    anios_sel = [
        st.selectbox("Año 1", range(2000, 2026), index=23),
        st.selectbox("Año 2", range(2000, 2026), index=20),
        st.selectbox("Año 3", range(2000, 2026), index=17)
    ]
    opacity = st.slider("Opacidad", 0.0, 1.0, 0.6, 0.1)

serie = serie_temporal(indice)

tab_mapas, tab_graficos = st.tabs(
    ["Mapas y estadísticas", "Gráficos Analíticos"]
)

# ===============================
# TAB 1 – MAPAS
# ===============================
with tab_mapas:
    cols = st.columns(3)

    for i, (col, anio) in enumerate(zip(cols, anios_sel)):
        with col:
            st.subheader(f"{indice} – {anio}")
            img = obtener_indice(anio, indice)
            tiles = img.getMapId(VIS_PARAMS[indice])

            mapa = folium.Map(
                location=[-16.42, -71.54],
                zoom_start=11,
                tiles="OpenStreetMap"
            )

            folium.TileLayer(
                tiles=tiles["tile_fetcher"].url_format,
                attr="Google Earth Engine",
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
                **Promedio:** {stats[indice+'_mean']:.3f}  
                **Mínimo:** {stats[indice+'_min']:.3f}  
                **Máximo:** {stats[indice+'_max']:.3f}
                """
            )

    st.divider()
    st.subheader("Evolución temporal (rango seleccionado)")

    rango = [d for d in serie if d["Valor"] is not None and min(anios_sel) <= d["Año"] <= max(anios_sel)]
    if rango:
        st.line_chart({str(d["Año"]): d["Valor"] for d in rango})
    else:
        st.warning("No hay datos suficientes.")

# ===============================
# TAB 2 – GRÁFICOS ANALÍTICOS
# ===============================
with tab_graficos:
    st.subheader(f"Evolución temporal del {indice}")
    completos = [d for d in serie if d["Valor"] is not None]
    st.line_chart({str(d["Año"]): d["Valor"] for d in completos})

    st.divider()
    st.subheader(f"Distribución del {indice} por periodos")

    anios = [d["Año"] for d in completos]
    valores = [d["Valor"] for d in completos]

    fig = go.Figure()
    fig.add_trace(go.Box(y=[v for a,v in zip(anios,valores) if a<=2006], name="2000–2006", marker_color="red"))
    fig.add_trace(go.Box(y=[v for a,v in zip(anios,valores) if 2007<=a<=2012], name="2007–2012", marker_color="orange"))
    fig.add_trace(go.Box(y=[v for a,v in zip(anios,valores) if a>=2013], name="2013–2025", marker_color="green"))

    st.plotly_chart(fig, use_container_width=True)

    st.divider()
    st.subheader(f"Análisis de anomalías del {indice}")

    media = sum(valores) / len(valores)
    std = (sum((v - media) ** 2 for v in valores) / len(valores)) ** 0.5
    anom = [v - media for v in valores]

    colores = []
    for a in anom:
        if abs(a) >= std:
            colores.append("darkgreen" if a > 0 else "darkred")
        elif abs(a) >= 0.5 * std:
            colores.append("green" if a > 0 else "red")
        else:
            colores.append("lightgreen" if a > 0 else "lightcoral")

    fig2 = go.Figure()

    fig2.add_trace(go.Bar(
        x=anios,
        y=anom,
        marker_color=colores,
        name="Anomalía"
    ))

    fig2.add_hline(
        y=0,
        line_width=2,
        line_color="black"
    )

    fig2.update_layout(
        title=f"Anomalías del {indice} respecto al promedio histórico",
        xaxis_title="Año",
        yaxis_title="Anomalía",
        showlegend=False
    )

    st.plotly_chart(fig2, use_container_width=True)

    st.markdown(
        f"""
        **Promedio histórico:** {media:.4f}  
        **Desviación estándar:** {std:.4f}
        """
    )

