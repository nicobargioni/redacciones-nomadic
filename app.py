import streamlit as st

st.set_page_config(
    page_title="Dashboard de Medios",
    page_icon="📊",
    layout="wide"
)

st.title("📊 Nomadic | Dashboard de Medios")
st.markdown("---")

st.markdown("### Esta página es para nosotros. NO VA A EXISTIR EN PRODUCCIÓN.")
st.info("📋 Los dashboards están disponibles a través de URLs que nosotros le vamos a dar al cliente.")
st.info("👈 En el sidebar de la izquierda están todas las páginas. ESTO NO LO VA A VER EL CLIENTE NI LA REDACCIÓN, ES PARA COMODIDAD DURANTE LA ETAPA DE PRE PRODUCCION.")
st.text("👈 Prestar atención a que cada página del sidebar indica en su nombre si es para la redacción o para el cliente.")
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

st.markdown("### ℹ️ Ejemplo de uso:")
st.markdown("Para ingresar al dashboard de **OKDiario** como **cliente**, la URL sería: `https://redacciones-nomadic.streamlit.app/okdiario-431468943` y las credenciales serían: usuario: okdiario y contraseña okdiario123")
st.markdown("Para ingresar al dashboard de **OKDiario** como **redacción**, la URL sería: `https://redacciones-nomadic.streamlit.app/redaccion-okdiario-20566` y las credenciales serían: usuario: okdiario y contraseña okdiario_red123")
st.markdown("---")
st.markdown("*Cada cuenta tiene 2 paneles: REDACCIÓN Y CLIENTE.*")
st.markdown("*La idea es que ambos grupos de usuarios -redacción y cliente- vean la data que le es de interés*")
