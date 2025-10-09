import streamlit as st

st.set_page_config(
    page_title="Dashboard de Medios",
    page_icon="📊",
    layout="wide"
)

# Ocultar sidebar
st.markdown("""
    <style>
    [data-testid="stSidebar"] {
        display: none !important;
    }
    section[data-testid="stSidebar"] {
        display: none !important;
    }
    </style>
""", unsafe_allow_html=True)

st.title("📊 Nomadic | Dashboard de Medios")
st.markdown("---")

st.markdown("### Esta página es para nosotros. NO VA A EXISTIR EN PRODUCCIÓN.")
st.info("📋 Los dashboards están disponibles a través de URLs que nosotros le vamos a dar al cliente.")
st.markdown("---")
st.markdown("### 🔑 Credenciales TEMPORALES de Acceso")
st.warning("⚠️ Estas credenciales son TEMPORALES y se modificarán en producción según decida el cliente.")

st.code("""
# Clientes por medio
clarin_cliente = "clarin123"
ole_cliente = "ole123"
elespanol_cliente = "elespanol123"
okdiario_cliente = "okdiario123"
mundodeportivo_cliente = "mundo123"
natgeo_cliente = "natgeo123"
vidae_cliente = "vidae123"
bumeran_cliente = "bumeran123"
sancor_cliente = "sancor123"

# Redacciones por medio
clarin_redaccion = "clarin_red123"
ole_redaccion = "ole_red123"
elespanol_redaccion = "elespanol_red123"
okdiario_redaccion = "okdiario_red123"
mundodeportivo_redaccion = "mundo_red123"
natgeo_redaccion = "natgeo_red123"
vidae_redaccion = "vidae_red123"
bumeran_redaccion = "bumeran_red123"
sancor_redaccion = "sancor_red123"
""", language="toml")

st.info("📝 Al pasar a producción, estas credenciales serán reemplazadas por las que defina cada cliente.")

st.markdown("### 📋 URLs de Acceso")
st.markdown("Cada medio tiene dos dashboards: uno para **Redacción** y otro para **Cliente**")

import pandas as pd

# Crear datos de la tabla
urls_data = {
    "Páginas de Redacción": [
        "https://redacciones-nomadic.streamlit.app/redaccion-clarin-85046",
        "https://redacciones-nomadic.streamlit.app/redaccion-ole-40453",
        "https://redacciones-nomadic.streamlit.app/redaccion-okdiario-20566",
        "https://redacciones-nomadic.streamlit.app/redaccion-elespanol-73498",
        "https://redacciones-nomadic.streamlit.app/redaccion-mundodeportivo-84048",
        "https://redacciones-nomadic.streamlit.app/redaccion-natgeo-78696",
        "https://redacciones-nomadic.streamlit.app/redaccion-vidae-15766",
        "https://redacciones-nomadic.streamlit.app/redaccion-bumeran-77169",
        "https://redacciones-nomadic.streamlit.app/redaccion-sancor-67127"
    ],
    "Páginas de Cliente": [
        "https://redacciones-nomadic.streamlit.app/clarin-106275640",
        "https://redacciones-nomadic.streamlit.app/ole-412346632",
        "https://redacciones-nomadic.streamlit.app/okdiario-431468943",
        "https://redacciones-nomadic.streamlit.app/elespanol-421272699",
        "https://redacciones-nomadic.streamlit.app/mundodeportivo-491737805",
        "https://redacciones-nomadic.streamlit.app/natgeo-770032477",
        "https://redacciones-nomadic.streamlit.app/vidae-599772643",
        "https://redacciones-nomadic.streamlit.app/bumeran-251450665",
        "https://redacciones-nomadic.streamlit.app/sancor-537029540"
    ]
}

df_urls = pd.DataFrame(urls_data)
st.dataframe(df_urls, use_container_width=True, hide_index=True)

st.markdown("---")
st.markdown("### ℹ️ Ejemplo de uso:")
st.markdown("Para ingresar al dashboard de **OKDiario** como **cliente**, usa la URL: `https://redacciones-nomadic.streamlit.app/okdiario-431468943`")
st.markdown("- Usuario: `okdiario_cliente` | Contraseña: `okdiario123`")
st.markdown("")
st.markdown("Para ingresar al dashboard de **OKDiario** como **redacción**, usa la URL: `https://redacciones-nomadic.streamlit.app/redaccion-okdiario-20566`")
st.markdown("- Usuario: `okdiario_redaccion` | Contraseña: `okdiario_red123`")
st.markdown("---")
st.markdown("*Cada cuenta tiene 2 paneles: REDACCIÓN Y CLIENTE.*")
st.markdown("*La idea es que ambos grupos de usuarios -redacción y cliente- vean la data que le es de interés*")
