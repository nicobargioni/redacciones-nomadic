import streamlit as st

st.set_page_config(
    page_title="Dashboard de Medios - Redacciones",
    page_icon="📊",
    layout="wide"
)

st.title("📊 Nomadic | Dashboard de Medios - Redacciones")
st.markdown("---")

st.markdown("### 📊 Dashboards Disponibles para Redacciones")

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("#### 📰 Clarín")
    st.markdown("[Ir al Dashboard de Clarín](https://redacciones-nomadic.streamlit.app/r/clarin)")
    st.markdown("#### 🇪🇸 El Español")
    st.markdown("[Ir al Dashboard de El Español](https://redacciones-nomadic.streamlit.app/r/elespanol)")
    st.markdown("#### 💫 Vidae")
    st.markdown("[Ir al Dashboard de Vidae](https://redacciones-nomadic.streamlit.app/r/vidae)")

with col2:
    st.markdown("#### ⚽ Olé")
    st.markdown("[Ir al Dashboard de Olé](https://redacciones-nomadic.streamlit.app/r/ole)")
    st.markdown("#### 🌍 National Geographic")
    st.markdown("[Ir al Dashboard de National Geographic](https://redacciones-nomadic.streamlit.app/r/natgeo)")
    st.markdown("#### 💼 Bumeran")
    st.markdown("[Ir al Dashboard de Bumeran](https://redacciones-nomadic.streamlit.app/r/bumeran)")
        
with col3:
    st.markdown("#### 🗞️ OK Diario")
    st.markdown("[Ir al Dashboard de OK Diario](https://redacciones-nomadic.streamlit.app/r/okdiario)")
    st.markdown("#### 🏆 Mundo Deportivo")
    st.markdown("[Ir al Dashboard de Mundo Deportivo](https://redacciones-nomadic.streamlit.app/r/mundodeportivo)")
    st.markdown("#### 🏥 Sancor")
    st.markdown("[Ir al Dashboard de Sancor](https://redacciones-nomadic.streamlit.app/r/sancor)")