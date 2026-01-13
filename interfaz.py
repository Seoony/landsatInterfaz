import streamlit as st
from Core.gee_init import inicializar_gee, obtener_zona_estudio

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
