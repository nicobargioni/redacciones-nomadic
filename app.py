import streamlit as st

st.set_page_config(
    page_title="Dashboard de Medios",
    page_icon="📊",
    layout="wide"
)

st.title("📊 Nomadic | Dashboard de Medios")
st.markdown("---")

st.markdown("### 📊 Dashboards Disponibles")

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("#### 📰 Clarín")
    st.markdown("[Ir al Dashboard de Clarín](https://redacciones-nomadic.streamlit.app/clarin)")
    st.markdown("#### 🇪🇸 El Español")
    st.markdown("[Ir al Dashboard de El Español](https://redacciones-nomadic.streamlit.app/elespanol)")
    st.markdown("#### 💫 Vidae")
    st.markdown("[Ir al Dashboard de Vidae](https://redacciones-nomadic.streamlit.app/vidae)")

with col2:
    st.markdown("#### ⚽ Olé")
    st.markdown("[Ir al Dashboard de Olé](https://redacciones-nomadic.streamlit.app/ole)")
    st.markdown("#### 🌍 National Geographic")
    st.markdown("[Ir al Dashboard de National Geographic](https://redacciones-nomadic.streamlit.app/natgeo)")
    st.markdown("#### 💼 Bumeran")
    st.markdown("[Ir al Dashboard de Bumeran](https://redacciones-nomadic.streamlit.app/bumeran)")
        
with col3:
    st.markdown("#### 🗞️ OK Diario")
    st.markdown("[Ir al Dashboard de OK Diario](https://redacciones-nomadic.streamlit.app/okdiario)")
    st.markdown("#### 🏆 Mundo Deportivo")
    st.markdown("[Ir al Dashboard de Mundo Deportivo](https://redacciones-nomadic.streamlit.app/mundodeportivo)")
    st.markdown("#### 🏥 Sancor")
    st.markdown("[Ir al Dashboard de Sancor](https://redacciones-nomadic.streamlit.app/sancor)")
    