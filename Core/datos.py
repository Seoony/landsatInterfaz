import ee
import streamlit as st
import pandas as pd

from Core.gee_init import asegurar_zona_estudio
from Core.indices import INDICES


# ── Selector de colección según año ─────────────────────────────────────────

def _coleccion_y_bandas(anio: int):
    if anio <= 2011:
        return (
            ee.ImageCollection("LANDSAT/LE07/C02/T1_L2"),
            ["SR_B1", "SR_B2", "SR_B3", "SR_B4", "SR_B5", "SR_B7"],
        )
    if anio == 2012:
        col = ee.ImageCollection("LANDSAT/LT05/C02/T1_L2").merge(
            ee.ImageCollection("LANDSAT/LE07/C02/T1_L2")
        )
        return col, ["SR_B1", "SR_B2", "SR_B3", "SR_B4", "SR_B5", "SR_B7"]

    return (
        ee.ImageCollection("LANDSAT/LC08/C02/T1_L2"),
        ["SR_B2", "SR_B3", "SR_B4", "SR_B5", "SR_B6", "SR_B7"],
    )


# ── Imagen de un índice para un año ─────────────────────────────────────────

@st.cache_data(show_spinner=False)
def obtener_indice(anio: int, indice: str):
    zona_estudio = asegurar_zona_estudio()
    coleccion, bandas_origen = _coleccion_y_bandas(anio)

    imagen = (
        coleccion
        .filterDate(f"{anio}-01-01", f"{anio}-12-31")
        .filterBounds(zona_estudio)
        .filter(ee.Filter.lt("CLOUD_COVER", 20))
        .median()
        .select(bandas_origen)
        .rename(["BLUE", "GREEN", "RED", "NIR", "SWIR1", "SWIR2"])
        .clip(zona_estudio)
    )

    return INDICES[indice](imagen).rename(indice)


# ── Estadísticas de un índice para un año ───────────────────────────────────

@st.cache_data(show_spinner=False)
def estadisticas_indice(anio: int, indice: str):
    zona_estudio = asegurar_zona_estudio()
    img = obtener_indice(anio, indice)

    stats = img.reduceRegion(
        reducer=(
            ee.Reducer.mean()
            .combine(ee.Reducer.min(), "", True)
            .combine(ee.Reducer.max(), "", True)
        ),
        geometry=zona_estudio,
        scale=30,
        maxPixels=1e9,
    )
    return stats.getInfo()


# ── Serie temporal ────────────────────────────────────────────────────────────

@st.cache_data(show_spinner=False)
def serie_temporal(indice: str, inicio: int = 2000, fin: int = 2025):
    zona_estudio = asegurar_zona_estudio()

    def calcular_valor(anio):
        anio_ee = ee.Number(anio)

        # 2012: merge Landsat 5 + 7 (bandas TM, igual que <=2011)
        # <=2011: Landsat 7   |   >=2013: Landsat 8
        col_l7  = ee.ImageCollection("LANDSAT/LE07/C02/T1_L2")
        col_l5  = ee.ImageCollection("LANDSAT/LT05/C02/T1_L2")
        col_l8  = ee.ImageCollection("LANDSAT/LC08/C02/T1_L2")

        bandas_tm = ["SR_B1", "SR_B2", "SR_B3", "SR_B4", "SR_B5", "SR_B7"]
        bandas_oli = ["SR_B2", "SR_B3", "SR_B4", "SR_B5", "SR_B6", "SR_B7"]

        coleccion = ee.ImageCollection(
            ee.Algorithms.If(
                anio_ee.lte(2011),
                col_l7,
                ee.Algorithms.If(
                    anio_ee.eq(2012),
                    col_l5.merge(col_l7),
                    col_l8,
                )
            )
        ).filterDate(
            ee.Date.fromYMD(anio_ee, 1, 1),
            ee.Date.fromYMD(anio_ee, 12, 31),
        ).filterBounds(zona_estudio).filter(
            ee.Filter.lt("CLOUD_COVER", 20)
        )

        def reducir():
            bandas = ee.List(
                ee.Algorithms.If(
                    anio_ee.lte(2012),   # TM para <=2011 y 2012
                    bandas_tm,
                    bandas_oli,
                )
            )
            img = (
                coleccion.median()
                .select(bandas)
                .rename(["BLUE", "GREEN", "RED", "NIR", "SWIR1", "SWIR2"])
            )
            ind = INDICES[indice](img).rename(indice)
            red = ind.reduceRegion(
                ee.Reducer.mean(), zona_estudio, 30, maxPixels=1e9
            )
            return ee.Algorithms.If(red.contains(indice), red.get(indice), None)

        return ee.Feature(
            None,
            {
                "Año":  anio_ee,
                "Valor": ee.Algorithms.If(coleccion.size().gt(0), reducir(), None),
            },
        )

    fc = ee.FeatureCollection(
        ee.List.sequence(inicio, fin).map(calcular_valor)
    )

    return [
        {
            "Año":   int(f["properties"]["Año"]),
            "Valor": f["properties"].get("Valor"),
        }
        for f in fc.getInfo()["features"]
    ]


# ── Tabla de puntos de muestreo desde Google Sheets ─────────────────────────

_URL_SHEETS = (
    "https://docs.google.com/spreadsheets/d/"
    "1yQ3TJRpGAGqSnSfGgQP4c9UwwDt-RZwS/export?format=xlsx"
)

_COLUMNAS = ["Punto", "Profundidad", "Fertilidad", "pH", "Humedad", "Temperatura"]


@st.cache_data(ttl=300, show_spinner=False)
def cargar_tabla_muestreo(url: str = _URL_SHEETS) -> pd.DataFrame:
    df = pd.read_excel(url)
    # Renombrar por posición (los encabezados del Sheet pueden variar)
    nuevas = list(_COLUMNAS) + list(df.columns[len(_COLUMNAS):])
    df.columns = nuevas
    df["Punto"] = df["Punto"].ffill()
    df = df.dropna(subset=["Profundidad"])
    df = (
        df.groupby("Punto", as_index=False)
        .head(2)
        .reset_index(drop=True)
    )
    return df