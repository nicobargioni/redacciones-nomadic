import streamlit as st

st.set_page_config(
    page_title="Dashboard de Medios",
    page_icon="📊",
    layout="wide"
)

st.title("📊 Nomadic | Dashboard de Medios")
st.markdown("---")


col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("### 📰 Clarín")
    st.markdown("[Ir al Dashboard de Clarín](https://redacciones-nomadic.streamlit.app/clarin)")
    

with col2:
    st.markdown("### ⚽ Olé")
    st.markdown("[Ir al Dashboard de Olé](https://redacciones-nomadic.streamlit.app/ole)")
    
        
with col3:
    st.markdown("### 🗞️ OK Diario")
    st.markdown("[Ir al Dashboard de OK Diario](https://redacciones-nomadic.streamlit.app/okdiario)")
    