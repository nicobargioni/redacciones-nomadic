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
    st.markdown("[Ir al Dashboard de Clarín](http://localhost:8502/clarin)")
    

with col2:
    st.markdown("### ⚽ Olé")
    st.markdown("[Ir al Dashboard de Olé](http://localhost:8502/ole)")
    
        
with col3:
    st.markdown("### 🗞️ OK Diario")
    st.markdown("[Ir al Dashboard de OK Diario](http://localhost:8502/okdiario)")
    