import ee
import os
import json
import streamlit as st

def inicializar_gee():
    """Inicializa Google Earth Engine con credenciales OAuth2"""
    try:
        client_id = os.getenv('EE_CLIENT_ID') or os.getenv('CLIENT_ID')
        client_secret = os.getenv('EE_CLIENT_SECRET') or os.getenv('CLIENT_SECRET')
        refresh_token = os.getenv('EE_REFRESH_TOKEN') or os.getenv('REFRESH_TOKEN')

        if client_id and client_secret and refresh_token:
            credentials = {
                "client_id": client_id,
                "client_secret": client_secret,
                "refresh_token": refresh_token,
                "type": "authorized_user"
            }

            cred_dir = os.path.join(os.path.expanduser("~"), ".config", "earthengine")
            os.makedirs(cred_dir, exist_ok=True)

            with open(os.path.join(cred_dir, "credentials"), "w") as f:
                json.dump(credentials, f)

        ee.Initialize(project="fourth-return-458106-r5")

    except Exception as e:
        raise RuntimeError(f"Error inicializando GEE: {e}")


def obtener_zona_estudio():
    """Obtiene la geometría de la zona de estudio desde GEE"""
    try:
        return ee.FeatureCollection(
            "projects/fourth-return-458106-r5/assets/uchumayo"
        ).geometry()
    except Exception as e:
        raise RuntimeError(f"Error al cargar zona de estudio: {e}")


def asegurar_zona_estudio():
    """
    Asegura que la zona de estudio esté cargada en session_state.
    Llama a esta función al inicio de cada página de Streamlit.
    """
    if "zona_estudio" not in st.session_state:
        try:
            inicializar_gee()
            st.session_state["zona_estudio"] = obtener_zona_estudio()
        except Exception as e:
            st.error(f"Error al inicializar el sistema: {str(e)}")
            st.stop()
    
    return st.session_state["zona_estudio"]