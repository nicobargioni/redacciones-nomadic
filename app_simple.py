import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(
    page_title="Dashboard de Medios - DEMO",
    page_icon="📊",
    layout="wide"
)

st.title("📊 Nomadic | Dashboard de Medios - DEMO")
st.markdown("---")

st.info("🔧 Versión de prueba para verificar deployment en Streamlit Cloud")

# Datos de ejemplo
sample_data = {
    'Medio': ['Clarín', 'Olé', 'OK Diario'],
    'Artículos': [150, 89, 76],
    'Page Views': [45000, 23000, 18000],
    'Usuarios': [12000, 8500, 6200]
}

df = pd.DataFrame(sample_data)

col1, col2, col3 = st.columns(3)

with col1:
    st.metric("📰 Total Artículos", df['Artículos'].sum())

with col2:
    st.metric("👁️ Total Page Views", f"{df['Page Views'].sum():,}")

with col3:
    st.metric("👥 Total Usuarios", f"{df['Usuarios'].sum():,}")

st.markdown("---")

# Gráfico simple
fig = px.bar(df, x='Medio', y='Page Views', title='Page Views por Medio')
st.plotly_chart(fig, use_container_width=True)

# Tabla de datos
st.subheader("📊 Datos de Ejemplo")
st.dataframe(df, use_container_width=True)

st.markdown("---")
st.success("✅ Si ves esto, el deployment funciona correctamente!")
st.info("👉 Configurar secrets en Streamlit Cloud para activar conexión a GA4")