import ee
import folium
import plotly.graph_objects as go
import streamlit as st
from streamlit_folium import st_folium
 
from Core.datos import estadisticas_indice, obtener_indice, serie_temporal
from Core.gee_init import asegurar_zona_estudio
from Core.indices import INDICES, VIS_PARAMS
 
# ── Contexto ─────────────────────────────────────────────────────────────────
zona_estudio = asegurar_zona_estudio()
 
# ── Interfaz – sidebar ───────────────────────────────────────────────────────
st.title("Análisis Multitemporal – Índices Landsat")
 
with st.sidebar:
    indice = st.selectbox("Índice espectral", list(INDICES.keys()))
    anios_sel = [
        st.selectbox("Año 1", range(2000, 2026), index=23),
        st.selectbox("Año 2", range(2000, 2026), index=20),
        st.selectbox("Año 3", range(2000, 2026), index=17),
    ]
    opacity = st.slider("Opacidad", 0.0, 1.0, 0.6, 0.1)
 
# Serie temporal (caché compartido con 1_Exploracion si ya se calculó)
serie = serie_temporal(indice)
 
tab_mapas, tab_graficos = st.tabs(["Mapas y estadísticas", "Gráficos Analíticos"])
 
# ── Tab 1 – Mapas ─────────────────────────────────────────────────────────────
with tab_mapas:
    cols = st.columns(3)
 
    for col, anio in zip(cols, anios_sel):
        with col:
            st.subheader(f"{indice} – {anio}")
 
            img   = obtener_indice(anio, indice)
            tiles = img.getMapId(VIS_PARAMS[indice])
 
            mapa = folium.Map(location=[-16.42, -71.54], zoom_start=11, tiles="OpenStreetMap")
            folium.TileLayer(
                tiles=tiles["tile_fetcher"].url_format,
                attr="Google Earth Engine",
                opacity=opacity,
            ).add_to(mapa)
 
            st_folium(mapa, width=450, height=380, key=f"mapa_{indice}_{anio}")
 
            stats = estadisticas_indice(anio, indice)
            st.markdown(
                f"**Promedio:** {stats[indice+'_mean']:.3f}  \n"
                f"**Mínimo:** {stats[indice+'_min']:.3f}  \n"
                f"**Máximo:** {stats[indice+'_max']:.3f}"
            )
 
    st.divider()
    st.subheader("Evolución temporal (rango seleccionado)")
    rango = [d for d in serie if d["Valor"] is not None and min(anios_sel) <= d["Año"] <= max(anios_sel)]
    if rango:
        st.line_chart({str(d["Año"]): d["Valor"] for d in rango})
    else:
        st.warning("No hay datos suficientes para el rango seleccionado.")

    MENSAJES_EVOLUCION = {
        "NDVI": f"Según la tendencia del valor de este índice vemos que se ha incrementado relativamente con el correr" 
                "de los años, pero sin embargo es muy bajo estando en centésimos, que indica que hay perdida de cobertura vegetal, aun baja.",
        "SAVI": "Según la tendencia del valor de este índice vemos que se ha incrementado relativamente con el correr de los años, es relativamente "
                "un poco mayor el NAVI pero sin embargo es muy bajo estando en rango de centésimos, lo cual sigue indicando que hay perdida de cobertura "
                "vegetal, aunque relativamente baja.",
        "EVI": "Según la tendencia del valor de este índice, es más sensible para mostrar el área con alta vegetación y vemos que se ha mantenido idéntico"
               "con el correr de los años, pero sin embargo es muy bajo estando en rango de décimos, lo cual sigue indicando que hay perdida de cobertura vegetal, "
               "aunque relativamente baja en algunas zonas.",
        "GNDVI": "Según la tendencia del valor de este índice vemos que se ha incrementado relativamente con el correr de los años, pero sin embargo es muy bajo" 
                 "estando en rango de centésimos, los valores bajos indican zonas relacionadas con bajo contenido de clorofila, indicador indirecto de fertilidad "
                 "y disponibilidad de nutrientes.",
        "LSWI": "Según la tendencia del valor de este índice vemos que se mantiene constante y con un valor negativo con el correr de los años, sus valores bajos "
                "indican sequía, riesgo de compactación y pérdida de estructura.",
        "NDWI": "Según la tendencia del valor de este índice vemos que se ha disminuido relativamente con el correr de los años, pero sin embargo es muy bajo estando" 
                "en rango de centésimos negativos, ayuda a discriminar humedad, que influye en la descomposición y aporte de materia orgánica. Enfocado en agua superficial "
                "y humedad del suelo. Útil para monitorear sequía agrícola y degradación por falta de agua.",
        "MNDWI": "Según la tendencia del valor de este índice vemos que a disminuido relativamente con el correr de los años, pero sin embargo es muy bajo estando en rango "
                 "de decimos negativos, ayuda a identificar zonas con pérdida de agua, indicador de degradación."
    }
    st.markdown(f"{MENSAJES_EVOLUCION[indice]}")
 
# ── Tab 2 – Gráficos analíticos ───────────────────────────────────────────────
with tab_graficos:
    completos = [d for d in serie if d["Valor"] is not None]
    anios     = [d["Año"]   for d in completos]
    valores   = [d["Valor"] for d in completos]
 
    # — Serie completa —
    st.subheader(f"Evolución temporal del {indice}")
    st.line_chart({str(a): v for a, v in zip(anios, valores)})
    MENSAJES_SERIES = {
        "NDVI": f"Este gráfico representa la evolución temporal del índice espectral NDVI, donde observamos" 
                "tendencias de incremento o disminución asociadas a procesos de degradación o recuperación del suelo" 
                "en el área de estudio, entre valores de 0.022 a 0.043, valores bajos, que de preferencia indicarían "
                "proceso de degradación o perdida de cubierta vegetal.",
        "SAVI": "Este gráfico representa la evolución temporal del índice espectral SAVI, donde observamos tendencias "
                "de incremento o disminución asociadas a procesos de degradación o recuperación del suelo en el área de "
                "estudio, entre valores de 0.03 a 0.09, valores bajos, que de preferencia indicarían proceso de degradación "
                "pérdida de cobertura vegetal.",
        "EVI": "Este gráfico representa la evolución temporal del índice espectral EVI, donde observamos tendencias de incremento "
                "o disminución asociadas a procesos de degradación o recuperación del suelo en el área de estudio, entre valores de "
                "-0.034 a 0.30, valores bajos, que de preferencia indicarían proceso de degradación y pérdida de cobertura vegetal.",
        "GNDVI": "Este gráfico representa la evolución temporal del índice espectral GNDVI, donde observamos tendencias de incremento"
                 "o disminución asociadas a perdida de agua y procesos de degradación o recuperación del suelo en el área de estudio, "
                 "entre valores de 0.07 a 0.15, valores bajos, que de preferencia indicarían bajo contenido de clorofila, indicador indirecto "
                 "de fertilidad y disponibilidad de nutrientes.",
        "LSWI": "Este gráfico representa la evolución temporal del índice espectral LSWI, donde observamos tendencias constantes, sin mayor "
                "variación asociadas a riesgo de compactación y pérdida de estructura, entre valores de -0.05 a -0.03.",
        "NDWI": "Este gráfico representa la evolución temporal del índice espectral NDWI, donde observamos tendencias de disminución asociadas "
                "a disminución de humedad de agua y procesos de sequía agrícola y degradación por falta de agua, esta entre valores de -0.06 a -0.11.",
        "MNDWI": "Este gráfico representa la evolución temporal del índice espectral MNDWI, donde observamos tendencias de mínima disminución asociadas "
                 "a zonas con pérdida de agua, indicador de degradación, esta entre valores de -0.011 y -0.015."
    }
    st.caption(
        "**Evolución temporal del índice espectral seleccionado. Permite identificar "
        f"tendencias de degradación o recuperación del suelo en el área de estudio.**\n\n{MENSAJES_SERIES[indice]}"
    )
 
    st.divider()
 
    # — Distribución por periodos —
    st.subheader(f"Distribución del {indice} por periodos")
    fig = go.Figure([
        go.Box(y=[v for a, v in zip(anios, valores) if a <= 2006],        name="2000–2006", marker_color="red"),
        go.Box(y=[v for a, v in zip(anios, valores) if 2007 <= a <= 2012], name="2007–2012", marker_color="orange"),
        go.Box(y=[v for a, v in zip(anios, valores) if a >= 2013],         name="2013–2025", marker_color="green"),
    ])
    st.plotly_chart(fig, use_container_width=True)
    st.caption(
        "**Variabilidad del índice espectral en distintos intervalos temporales. "
        "Facilita la comparación de dispersión y estabilidad de los datos.**"
    )
 
    st.divider()
 
    # — Anomalías —
    st.subheader(f"Análisis de anomalías del {indice}")
 
    media = sum(valores) / len(valores)
    std   = (sum((v - media) ** 2 for v in valores) / len(valores)) ** 0.5
    anom  = [v - media for v in valores]
    
    def _color(a):
        if abs(a) >= std:       return "darkgreen"  if a > 0 else "darkred"
        if abs(a) >= 0.5 * std: return "green"      if a > 0 else "red"
        return                         "lightgreen" if a > 0 else "lightcoral"
 
    fig2 = go.Figure([
        go.Bar(x=anios, y=anom, marker_color=[_color(a) for a in anom], name="Anomalía")
    ])
    fig2.add_hline(y=0, line_width=2, line_color="black")
    fig2.update_layout(
        title=f"Anomalías del {indice} respecto al promedio histórico",
        xaxis_title="Año",
        yaxis_title="Anomalía",
        showlegend=False,
    )
    MENSAJES_ANOMALIAS = {
        "NDVI": f"Este gráfico identifica valores atípicos que se desvían del comportamiento promedio del índice espectral (los que están en color rojo oscuro y verde oscuro)"
                ", los cuales pueden estar asociados a eventos ambientales extremos o cambios abruptos en las condiciones del suelo. Y que claramente muestran valore que oscilan"
                "entre -0.015 y 0.025 valores que indican que existe procesos de degradación del suelo.",
        "SAVI": "Este gráfico identifica valores atípicos que se desvían del comportamiento promedio del índice espectral (los que están en color rojo oscuro y verde oscuro), los "
                "cuales pueden estar asociados a eventos ambientales extremos o cambios abruptos en las condiciones del suelo. Y que claramente muestran valore que oscilan entre -0.025 "
                "y 0.038 valores que indican que existe procesos de degradación del suelo.",
        "EVI": "",
        "GNDVI": "Este gráfico identifica valores atípicos que se desvían del comportamiento promedio del índice espectral (los que están en color rojo oscuro y verde oscuro son los que "
                 "sobrepasan la desviación estándar), los cuales pueden estar asociados a eventos ambientales extremos o cambios abruptos en las condiciones del suelo. Y que claramente "
                 "muestran valore que oscilan entre -0.015 y 0.030 valores que indican que existe bajo contenido de clorofila, por lo tanto, baja fertilidad y disponibilidad de nutrientes.",
        "LSWI": "Este gráfico identifica valores atípicos que se desvían del comportamiento promedio del índice espectral (los que están en color rojo oscuro y verde oscuro son los que sobrepasan "
                "la desviación estándar), los cuales pueden estar asociados a eventos de riesgo de compactación y pérdida de estructura. Y que claramente muestran valore que oscilan entre -0.005 y 0.020.",
        "NDWI": "El siguiente gráfico identifica valores atípicos que se desvían del comportamiento promedio del índice espectral (los que están en color rojo oscuro y verde oscuro son los que sobrepasan "
                "la desviación estándar), los cuales pueden estar asociados a eventos de riesgo de sequía agrícola y degradación por falta de agua. Y que claramente muestran valore que oscilan entre 0.015 y -0.025",
        "MNDWI": "El gráfico identifica valores atípicos que se desvían del comportamiento promedio del índice espectral (los que están en color rojo oscuro y verde oscuro son los que sobrepasan la desviación estándar), "
                 "los cuales pueden estar asociados a zonas con pérdida de agua, indicador de degradación. Y que claramente muestran valore que oscilan entre 0.015 y -0.020."
    }
    st.plotly_chart(fig2, use_container_width=True)
    st.caption(f"**Valores atípicos que se desvían del comportamiento promedio. Pueden estar asociados a eventos ambientales extremos o cambios abruptos en el suelo.**\n\n {MENSAJES_ANOMALIAS[indice]}")
    st.markdown(
        f"**Promedio histórico:** {media:.4f}  \n"
        f"**Desviación estándar:** {std:.4f}"
    )