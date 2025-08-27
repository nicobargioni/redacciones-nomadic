import streamlit as st

st.set_page_config(
    page_title="Dashboard de Medios",
    page_icon="📊",
    layout="wide"
)

st.title("📊 Nomadic | Dashboard de Medios")
st.markdown("---")

st.markdown("### 🎯 Seleccione su perfil de acceso")

col1, col2 = st.columns(2)

with col1:
    st.markdown("#### 📝 Redacciones")
    st.markdown("Acceso completo para equipos de redacción")
    st.markdown("[🔗 Acceder como Redacción](https://redacciones-nomadic.streamlit.app/redacciones)")
    
with col2:
    st.markdown("#### 👥 Clientes") 
    st.markdown("Vista personalizada para clientes")
    st.markdown("[🔗 Acceder como Cliente](https://redacciones-nomadic.streamlit.app/clientes)")

st.markdown("---")
st.markdown("*Selecciona tu perfil para acceder a los dashboards correspondientes*")