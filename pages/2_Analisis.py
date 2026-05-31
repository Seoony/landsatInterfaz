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
 
# ── Tab 2 – Gráficos analíticos ───────────────────────────────────────────────
with tab_graficos:
    completos = [d for d in serie if d["Valor"] is not None]
    anios     = [d["Año"]   for d in completos]
    valores   = [d["Valor"] for d in completos]
 
    # — Serie completa —
    st.subheader(f"Evolución temporal del {indice}")
    st.line_chart({str(a): v for a, v in zip(anios, valores)})
    st.caption(
        "Evolución temporal del índice espectral seleccionado. Permite identificar "
        "tendencias de degradación o recuperación del suelo en el área de estudio."
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
        "Variabilidad del índice espectral en distintos intervalos temporales. "
        "Facilita la comparación de dispersión y estabilidad de los datos."
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
    st.plotly_chart(fig2, use_container_width=True)
    st.caption("Valores atípicos que se desvían del comportamiento promedio. Pueden estar asociados a eventos ambientales extremos o cambios abruptos en el suelo.")
    st.markdown(
        f"**Promedio histórico:** {media:.4f}  \n"
        f"**Desviación estándar:** {std:.4f}"
    )