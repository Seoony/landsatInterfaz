import ee
import streamlit as st
from Core.gee_init import zona_estudio
from Core.indices import INDICES


@st.cache_data(show_spinner=False)
def obtener_indice(anio, indice):

    if anio <= 2011:
        coleccion = ee.ImageCollection("LANDSAT/LE07/C02/T1_L2")
        bandas_origen = ["SR_B1","SR_B2","SR_B3","SR_B4","SR_B5","SR_B7"]
    else:
        coleccion = ee.ImageCollection("LANDSAT/LC08/C02/T1_L2")
        bandas_origen = ["SR_B2","SR_B3","SR_B4","SR_B5","SR_B6","SR_B7"]

    imagen = (
        coleccion
        .filterDate(f"{anio}-01-01", f"{anio}-12-31")
        .filterBounds(zona_estudio)
        .filter(ee.Filter.lt("CLOUD_COVER", 20))
        .median()
        .select(bandas_origen)
        .rename(["BLUE","GREEN","RED","NIR","SWIR1","SWIR2"])
        .clip(zona_estudio)
    )

    # 👉 aquí ya están GARANTIZADAS todas las bandas
    img_indice = INDICES[indice](imagen).rename(indice)

    return img_indice


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
def serie_temporal(indice, inicio=2000, fin=2025):

    def calcular_valor(anio):
        img = obtener_indice(anio, indice)

        reduccion = img.reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=zona_estudio,
            scale=30,
            maxPixels=1e9
        )

        return ee.Feature(
            None,
            {
                "Año": anio,
                "Valor": ee.Algorithms.If(
                    reduccion.contains(indice),
                    reduccion.get(indice),
                    None
                )
            }
        )

    fc = ee.FeatureCollection(
        ee.List.sequence(inicio, fin).map(calcular_valor)
    )

    datos = fc.getInfo()

    return [
        {
            "Año": int(f["properties"]["Año"]),
            "Valor": f["properties"].get("Valor")
        }
        for f in datos["features"]
    ]


def grafico_rango_anios(serie, anios_sel, titulo):

    a_ini, a_fin = min(anios_sel), max(anios_sel)

    anios = []
    valores = []

    for d in serie:
        if d["Valor"] is not None and a_ini <= d["Año"] <= a_fin:
            anios.append(d["Año"])
            valores.append(d["Valor"])

    if valores:
        st.subheader(titulo)
        st.line_chart({str(a): v for a, v in zip(anios, valores)})
    else:
        st.warning("No hay datos suficientes para generar el gráfico.")
