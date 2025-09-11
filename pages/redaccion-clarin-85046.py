import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import (
    load_google_sheet_data, 
    get_ga4_data, 
    filter_media_urls,
    merge_sheets_with_ga4,
    create_media_config,
    check_login,
    get_ga4_pageviews_data,
    get_ga4_historical_data,
    get_ga4_growth_data,
    get_ga4_growth_data_custom,
    format_growth_percentage,
    get_monthly_pageviews_by_sheets
)

# Configuración de la página
st.set_page_config(
    page_title="Dashboard Clarín - Redacción",
    page_icon="📰",
    layout="wide"
)

# Verificar login antes de mostrar contenido
if not check_login('clarin', page_type='redaccion'):
    st.stop()

# Obtener configuración del medio
media_config = create_media_config()['clarin']

st.title(f"{media_config['icon']} Dashboard de {media_config['name']}")
st.markdown("---")

# Sidebar con opciones
st.sidebar.header("⚙️ Configuración")

# Selector de rango de fechas para GA4
date_option = st.sidebar.selectbox(
    "Tipo de rango de fechas:",
    ["Preestablecido", "Personalizado"],
    key="date_option_clarin"
)

if date_option == "Preestablecido":
    date_range = st.sidebar.selectbox(
        "Rango de datos GA4:",
        ["7daysAgo", "14daysAgo", "30daysAgo", "90daysAgo"],
        format_func=lambda x: {
            "7daysAgo": "Últimos 7 días",
            "14daysAgo": "Últimos 14 días", 
            "30daysAgo": "Últimos 30 días",
            "90daysAgo": "Últimos 90 días"
        }[x],
        key="preset_range_clarin"
    )
    start_date_param = date_range
    end_date_param = "today"
else:
    col1, col2 = st.sidebar.columns(2)
    with col1:
        start_date_custom = st.date_input(
            "Fecha inicio:",
            value=datetime.now() - timedelta(days=7),
            key="start_date_clarin"
        )
    with col2:
        end_date_custom = st.date_input(
            "Fecha fin:",
            value=datetime.now(),
            key="end_date_clarin"
        )
    
    # Convertir fechas a formato GA4
    start_date_param = start_date_custom.strftime("%Y-%m-%d")
    end_date_param = end_date_custom.strftime("%Y-%m-%d")
    
    # Validar que la fecha de inicio sea anterior a la fecha de fin
    if start_date_custom > end_date_custom:
        st.sidebar.error("⚠️ La fecha de inicio debe ser anterior a la fecha de fin")
        start_date_param = "7daysAgo"
        end_date_param = "today"

# Botón de actualización
if st.sidebar.button("🔄 Actualizar datos"):
    st.cache_data.clear()
    st.rerun()

# Usar archivo de credenciales de medios (funciona para todas las propiedades)
credentials_file = "credentials_analytics_acceso_medios.json"

# Cargar datos
with st.spinner('Cargando datos...'):
    # Cargar datos del Google Sheet
    sheets_df = load_google_sheet_data()
    
    # Filtrar solo URLs de Clarín
    if sheets_df is not None:
        sheets_filtered = filter_media_urls(sheets_df, media_config['domain'])
    else:
        sheets_filtered = pd.DataFrame()
    
    # Cargar datos de GA4
    ga4_df = get_ga4_data(
        media_config['property_id'],
        credentials_file,
        start_date=start_date_param,
        end_date=end_date_param
    )

# Verificar si hay datos
if sheets_filtered.empty and (ga4_df is None or ga4_df.empty):
    st.error("⚠️ No se encontraron datos para mostrar")
    st.info(f"""
    **Posibles causas:**
    - No hay URLs de {media_config['domain']} en el Google Sheet
    - Error al conectar con Google Analytics 4
    - Credenciales incorrectas o sin permisos para la propiedad {media_config['property_id']}
    """)
else:
    # Agregar filtro por autor si hay datos
    author_filter = None
    if not sheets_filtered.empty and 'autor' in sheets_filtered.columns:
        authors = sorted(sheets_filtered['autor'].dropna().unique())
        author_filter = st.sidebar.multiselect(
            "👤 Filtrar por Autor:",
            options=authors,
            default=None,
            key="author_filter_clarin"
        )
        
        if author_filter:
            sheets_filtered = sheets_filtered[sheets_filtered['autor'].isin(author_filter)]
            st.sidebar.info(f"📊 {len(sheets_filtered)} artículos seleccionados")
    
    # Agregar filtros por fuente y medio de GA4
    source_filter = None
    medium_filter = None
    
    if ga4_df is not None and not ga4_df.empty:
        # Filtro por fuente (sessionSource)
        if 'sessionSource' in ga4_df.columns:
            sources = sorted(ga4_df['sessionSource'].dropna().unique())
            if len(sources) > 0:
                source_filter = st.sidebar.multiselect(
                    "🌐 Filtrar por Fuente:",
                    options=sources,
                    default=None,
                    key="source_filter_clarin",
                    help="Fuente del tráfico (Google, Facebook, etc.)"
                )
        
        # Filtro por medio (sessionMedium)
        if 'sessionMedium' in ga4_df.columns:
            mediums = sorted(ga4_df['sessionMedium'].dropna().unique())
            if len(mediums) > 0:
                medium_filter = st.sidebar.multiselect(
                    "📡 Filtrar por Medio:",
                    options=mediums,
                    default=None,
                    key="medium_filter_clarin",
                    help="Medio del tráfico (organic, cpc, referral, etc.)"
                )
    
    # Métricas de datos cargados
    st.sidebar.metric("URLs en Sheet", len(sheets_filtered) if not sheets_filtered.empty else 0)
    if ga4_df is not None:
        st.sidebar.metric("Páginas en GA4", ga4_df['pagePath'].nunique())
    else:
        st.sidebar.metric("Páginas en GA4", 0)
    
    # Mergear datos si ambos están disponibles
    if not sheets_filtered.empty and ga4_df is not None and not ga4_df.empty:
        # Aplicar filtros de fuente y medio a GA4 antes del merge
        ga4_filtered = ga4_df.copy()
        
        if source_filter:
            ga4_filtered = ga4_filtered[ga4_filtered['sessionSource'].isin(source_filter)]
        
        if medium_filter:
            ga4_filtered = ga4_filtered[ga4_filtered['sessionMedium'].isin(medium_filter)]
        
        if not ga4_filtered.empty:
            merged_df = merge_sheets_with_ga4(sheets_filtered, ga4_filtered, media_config['domain'])
            
            # Mostrar información de filtros aplicados
            if source_filter or medium_filter:
                filter_info = []
                if source_filter:
                    filter_info.append(f"Fuentes: {len(source_filter)}")
                if medium_filter:
                    filter_info.append(f"Medios: {len(medium_filter)}")
                st.sidebar.success(f"🎯 Filtros GA4: {', '.join(filter_info)}")
        else:
            st.warning("⚠️ Los filtros de fuente/medio no devolvieron datos de GA4")
            merged_df = sheets_filtered  # Solo datos del sheet
        
        # Obtener URLs del Sheet filtradas para las métricas
        sheets_urls_for_metrics = None
        if not sheets_filtered.empty and 'url_normalized' in sheets_filtered.columns:
            sheets_urls_for_metrics = sheets_filtered['url_normalized'].dropna().unique().tolist()
        
        # Obtener pageviews del mes actual
        monthly_pageviews = 0
        if sheets_urls_for_metrics:
            with st.spinner("Cargando métricas del mes..."):
                monthly_pageviews = get_monthly_pageviews_by_sheets(
                    media_config['property_id'],
                    credentials_file,
                    sheets_urls_for_metrics,
                    media_config['domain']
                )
        
        # Métricas principales - Diseño más grande y prominente
        articles_count = len(sheets_filtered) if not sheets_filtered.empty else 0
        
        st.markdown(f"""
        <div style="text-align: center; padding: 20px 0;">
            <div style="margin-bottom: 30px;">
                <h2 style="color: #1f77b4; font-size: 24px; margin-bottom: 5px;">📊 Pageviews del mes (solo URLs del Sheet)</h2>
                <h1 style="color: #1f77b4; font-size: 48px; font-weight: bold; margin: 0;">{monthly_pageviews:,}</h1>
            </div>
            <div>
                <h3 style="color: #666; font-size: 20px; margin: 0;">📰 {articles_count:,} notas generadas</h3>
            </div>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("---")
        
        # Tabs para diferentes vistas
        tab1, tab3, tab_crecimiento, tab_historico = st.tabs(["📋 Datos", "🔝 Top Páginas", "📈 Crecimiento", "📈 Histórico"])
        
        with tab1:
            st.subheader("📋 Datos Combinados (Sheet + GA4)")
            
            # Búsqueda
            search = st.text_input("🔍 Buscar:", "")
            display_df = merged_df.copy()
            
            if search:
                mask = display_df.astype(str).apply(lambda x: x.str.contains(search, case=False, na=False)).any(axis=1)
                display_df = display_df[mask]
            
            # Seleccionar solo las columnas específicas
            columns_to_show = ['titulo', 'url', 'datePub', 'autor', 'screenPageViews']
            available_columns = [col for col in columns_to_show if col in display_df.columns]
            
            if available_columns:
                display_filtered = display_df[available_columns].copy()
                
                # Renombrar columnas para mejor presentación
                column_names = {
                    'titulo': 'Título',
                    'url': 'URL',
                    'datePub': 'Fecha de Publicación',
                    'autor': 'Autor',
                    'screenPageViews': 'Page Views'
                }
                display_filtered = display_filtered.rename(columns=column_names)
                
                # Mostrar DataFrame filtrado
                st.dataframe(display_filtered, use_container_width=True, height=500)
            else:
                st.warning("No se encontraron las columnas requeridas en los datos")
            
            # Descarga
            csv = display_df.to_csv(index=False)
            st.download_button(
                label="📥 Descargar datos",
                data=csv,
                file_name=f"clarin_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
        
        with tab3:
            st.subheader("🔝 Top Páginas")
            
            # Selector de métrica
            metric_options = [col for col in ['sessions', 'totalUsers', 'screenPageViews', 'newUsers'] 
                            if col in merged_df.columns]
            
            if metric_options:
                selected_metric = st.selectbox("Seleccionar métrica:", metric_options)
                top_n = st.slider("Número de páginas a mostrar:", 5, 50, 20)
                
                # Top páginas
                top_df = merged_df.nlargest(top_n, selected_metric)[['url_normalized', selected_metric]]
                
                # Gráfico
                fig_top = go.Figure(data=[
                    go.Bar(
                        x=top_df[selected_metric],
                        y=top_df['url_normalized'],
                        orientation='h',
                        marker_color=media_config['color']
                    )
                ])
                fig_top.update_layout(
                    title=f"Top {top_n} Páginas por {selected_metric}",
                    xaxis_title=selected_metric,
                    yaxis_title="URL",
                    height=max(400, top_n * 20),
                    yaxis=dict(autorange="reversed")
                )
                st.plotly_chart(fig_top, use_container_width=True)
                
                # Tabla de datos
                st.dataframe(top_df, use_container_width=True)
        
        with tab_crecimiento:
            st.subheader("📈 Crecimiento")
            
            # Selector de tipo de comparación
            col1, col2 = st.columns([1, 3])
            
            with col1:
                comparison_type = st.selectbox(
                    "Tipo de comparación:",
                    ["day", "week", "month", "90days", "custom"],
                    format_func=lambda x: {
                        "day": "Día vs Día anterior",
                        "week": "Semana vs Semana anterior", 
                        "month": "Mes vs Mes anterior",
                        "90days": "90 días vs 90 días anteriores",
                        "custom": "Período personalizado"
                    }[x],
                    key="comparison_type_redac_clarin"
                )
            
            # Obtener URLs normalizadas del Sheet para filtrar
            sheets_urls = None
            if not sheets_filtered.empty and 'url_normalized' in merged_df.columns:
                sheets_urls = merged_df['url_normalized'].dropna().unique().tolist()
            
            # Si es personalizado, mostrar selectores de fecha
            if comparison_type == "custom":
                st.markdown("**Período Actual:**")
                col1, col2 = st.columns(2)
                with col1:
                    current_start = st.date_input(
                        "Inicio actual:",
                        value=datetime.now() - timedelta(days=7),
                        key="growth_current_start_redac_clarin"
                    )
                with col2:
                    current_end = st.date_input(
                        "Fin actual:",
                        value=datetime.now(),
                        key="growth_current_end_redac_clarin"
                    )
                
                st.markdown("**Período de Comparación:**")
                col3, col4 = st.columns(2)
                with col3:
                    previous_start = st.date_input(
                        "Inicio comparación:",
                        value=datetime.now() - timedelta(days=14),
                        key="growth_previous_start_redac_clarin"
                    )
                with col4:
                    previous_end = st.date_input(
                        "Fin comparación:",
                        value=datetime.now() - timedelta(days=8),
                        key="growth_previous_end_redac_clarin"
                    )
                
                # Obtener datos personalizados
                growth_data = get_ga4_growth_data_custom(
                    media_config['property_id'],
                    credentials_file,
                    current_start,
                    current_end,
                    previous_start,
                    previous_end,
                    sheets_urls
                )
            else:
                # Obtener datos predefinidos
                growth_data = get_ga4_growth_data(
                    media_config['property_id'],
                    credentials_file,
                    comparison_type,
                    sheets_urls
                )
            
            if growth_data:
                st.success(f"📊 Comparando: {growth_data['period_name']}")
                
                # Mostrar períodos
                col1, col2 = st.columns(2)
                with col1:
                    st.info(f"**Período Actual:** {growth_data['current_period']}")
                with col2:
                    st.info(f"**Período Anterior:** {growth_data['previous_period']}")
                
                st.markdown("---")
                
                # Métricas de crecimiento
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    pv_data = growth_data['data']['pageviews']
                    growth_pct = pv_data['growth_percentage']
                    delta_color = "normal" if growth_pct >= 0 or growth_pct == float('inf') else "inverse"
                    st.metric(
                        "📊 Page Views",
                        f"{pv_data['current']:,}",
                        delta=format_growth_percentage(growth_pct, pv_data['growth_absolute']),
                        delta_color=delta_color
                    )
                
                with col2:
                    sessions_data = growth_data['data']['sessions']
                    growth_pct = sessions_data['growth_percentage']
                    delta_color = "normal" if growth_pct >= 0 or growth_pct == float('inf') else "inverse"
                    st.metric(
                        "👥 Sesiones",
                        f"{sessions_data['current']:,}",
                        delta=format_growth_percentage(growth_pct, sessions_data['growth_absolute']),
                        delta_color=delta_color
                    )
                
                with col3:
                    users_data = growth_data['data']['users']
                    growth_pct = users_data['growth_percentage']
                    delta_color = "normal" if growth_pct >= 0 or growth_pct == float('inf') else "inverse"
                    st.metric(
                        "🔗 Usuarios",
                        f"{users_data['current']:,}",
                        delta=format_growth_percentage(growth_pct, users_data['growth_absolute']),
                        delta_color=delta_color
                    )
                
                st.markdown("---")
                
                # Gráfico de comparación
                metrics = ['pageviews', 'sessions', 'users']
                metric_names = ['Page Views', 'Sesiones', 'Usuarios']
                current_values = [growth_data['data'][m]['current'] for m in metrics]
                previous_values = [growth_data['data'][m]['previous'] for m in metrics]
                
                # Crear DataFrame para el gráfico
                chart_data = pd.DataFrame({
                    'Métrica': metric_names + metric_names,
                    'Valor': current_values + previous_values,
                    'Período': ['Actual'] * 3 + ['Anterior'] * 3
                })
                
                fig_comparison = px.bar(
                    chart_data,
                    x='Métrica',
                    y='Valor',
                    color='Período',
                    barmode='group',
                    title=f'Comparación de Métricas: {growth_data["period_name"]}',
                    color_discrete_map={
                        'Actual': media_config['color'],
                        'Anterior': '#cccccc'
                    }
                )
                st.plotly_chart(fig_comparison, use_container_width=True)
                
                # Gráfico de crecimiento porcentual
                growth_percentages = [growth_data['data'][m]['growth_percentage'] for m in metrics]
                colors = ['green' if x >= 0 else 'red' for x in growth_percentages]
                
                fig_growth = go.Figure(data=[
                    go.Bar(
                        x=metric_names,
                        y=growth_percentages,
                        marker_color=colors,
                        text=[f"{x:+.1f}%" for x in growth_percentages],
                        textposition='auto',
                    )
                ])
                
                fig_growth.update_layout(
                    title=f'Crecimiento Porcentual: {growth_data["period_name"]}',
                    yaxis_title='Crecimiento (%)',
                    showlegend=False
                )
                
                # Agregar línea en y=0
                fig_growth.add_hline(y=0, line_dash="dash", line_color="gray")
                
                st.plotly_chart(fig_growth, use_container_width=True)
                
            else:
                st.error("❌ No se pudieron obtener los datos de crecimiento")
        
        with tab_historico:
            st.subheader("📈 Histórico")
            
            # Controles de configuración del histórico
            col1, col2 = st.columns([1, 1])
            
            with col1:
                # Selector de período
                historical_period = st.selectbox(
                    "Período de análisis:",
                    ["3months", "6months", "1year", "custom"],
                    format_func=lambda x: {
                        "3months": "📅 Últimos 3 meses",
                        "6months": "📅 Últimos 6 meses",
                        "1year": "📅 Último año",
                        "custom": "📅 Personalizado"
                    }[x],
                    key="historical_period_clarin"
                )
            
            with col2:
                # Selector de granularidad temporal
                time_granularity = st.selectbox(
                    "Granularidad:",
                    ["day", "week", "month"],
                    format_func=lambda x: {
                        "day": "📊 Diario",
                        "week": "📊 Semanal",
                        "month": "📊 Mensual"
                    }[x],
                    key="time_granularity_clarin"
                )
            
            # Configurar fechas según el período seleccionado
            if historical_period == "custom":
                col3, col4 = st.columns(2)
                with col3:
                    hist_start_date = st.date_input(
                        "Fecha inicio:",
                        value=datetime.now() - timedelta(days=90),
                        key="hist_start_clarin"
                    )
                with col4:
                    hist_end_date = st.date_input(
                        "Fecha fin:",
                        value=datetime.now(),
                        key="hist_end_clarin"
                    )
            else:
                # Períodos predefinidos
                today = datetime.now()
                if historical_period == "3months":
                    hist_start_date = today - timedelta(days=90)
                elif historical_period == "6months":
                    hist_start_date = today - timedelta(days=180)
                else:  # 1year
                    hist_start_date = today - timedelta(days=365)
                hist_end_date = today
            
            # Obtener URLs del Sheet para filtrar
            sheets_urls = None
            if not sheets_filtered.empty and 'url_normalized' in sheets_filtered.columns:
                sheets_urls = sheets_filtered['url_normalized'].dropna().unique().tolist()
            
            # Cargar datos históricos
            with st.spinner("Cargando datos históricos..."):
                historical_df = get_ga4_historical_data(
                    media_config['property_id'],
                    credentials_file,
                    hist_start_date,
                    hist_end_date,
                    time_granularity,
                    sheets_urls,
                    media_config['domain']
                    media_config['property_id'],
                    credentials_file,
                    hist_start_date,
                    hist_end_date,
                    time_granularity,
                    sheets_urls
                )
            
            if historical_df is not None and not historical_df.empty:
                st.success(f"📊 Datos históricos cargados: {len(historical_df)} registros")
                
                # Agregar información de autores desde el Sheet si está disponible
                if not sheets_filtered.empty and 'autor' in sheets_filtered.columns:
                    # Crear mapping de URL -> autor
                    url_author_map = sheets_filtered.set_index('url_normalized')['autor'].to_dict()
                    historical_df['autor'] = historical_df['url_normalized'].map(url_author_map)
                
                st.markdown("---")
                
                # 1. GRÁFICO: Histórico de Notas
                st.subheader("📊 Histórico de Notas")
                st.caption("Pageviews acumuladas de todas las publicaciones en el tiempo")
                
                # Agrupar por período y sumar pageviews
                notes_historical = historical_df.groupby('period')['pageviews'].sum().reset_index()
                notes_historical = notes_historical.sort_values('period')
                
                if not notes_historical.empty:
                    fig_notes = px.line(
                        notes_historical,
                        x='period',
                        y='pageviews',
                        title=f'Histórico de Pageviews - {time_granularity.title()}',
                        labels={
                            'period': 'Fecha',
                            'pageviews': 'Pageviews'
                        },
                        color_discrete_sequence=[media_config['color']]
                    )
                    
                    fig_notes.update_layout(
                        xaxis_title='Fecha',
                        yaxis_title='Pageviews',
                        hovermode='x unified'
                    )
                    
                    # Agregar marcadores
                    fig_notes.update_traces(
                        mode='lines+markers',
                        line=dict(width=3),
                        marker=dict(size=6)
                    )
                    
                    st.plotly_chart(fig_notes, use_container_width=True)
                    
                    # Métricas del período
                    total_pageviews_period = notes_historical['pageviews'].sum()
                    avg_pageviews_period = notes_historical['pageviews'].mean()
                    
                    col_met1, col_met2, col_met3 = st.columns(3)
                    with col_met1:
                        st.metric("📊 Total Pageviews", f"{total_pageviews_period:,.0f}")
                    with col_met2:
                        st.metric("📈 Promedio por Período", f"{avg_pageviews_period:,.0f}")
                    with col_met3:
                        best_period = notes_historical.loc[notes_historical['pageviews'].idxmax(), 'period']
                        st.metric("🏆 Mejor Período", best_period.strftime('%d/%m/%Y'))
                else:
                    st.info("No hay datos suficientes para mostrar el histórico de notas")
                
                st.markdown("---")
                
                # 2. GRÁFICO: Histórico por Autor
                st.subheader("👤 Histórico por Autor")
                st.caption("Pageviews acumuladas por autor en el tiempo")
                
                if 'autor' in historical_df.columns and historical_df['autor'].notna().any():
                    # Selector de autor
                    available_authors = sorted(historical_df['autor'].dropna().unique())
                    selected_author = st.selectbox(
                        "Seleccionar autor:",
                        available_authors,
                        key="selected_author_historical_clarin"
                    )
                    
                    # Filtrar datos por autor seleccionado
                    author_data = historical_df[historical_df['autor'] == selected_author]
                    author_historical = author_data.groupby('period')['pageviews'].sum().reset_index()
                    author_historical = author_historical.sort_values('period')
                    
                    if not author_historical.empty:
                        fig_author = px.line(
                            author_historical,
                            x='period',
                            y='pageviews',
                            title=f'Histórico de Pageviews - {selected_author}',
                            labels={
                                'period': 'Fecha',
                                'pageviews': 'Pageviews'
                            },
                            color_discrete_sequence=['#ff6b35']
                        )
                        
                        fig_author.update_layout(
                            xaxis_title='Fecha',
                            yaxis_title='Pageviews',
                            hovermode='x unified'
                        )
                        
                        # Agregar marcadores
                        fig_author.update_traces(
                            mode='lines+markers',
                            line=dict(width=3),
                            marker=dict(size=6)
                        )
                        
                        st.plotly_chart(fig_author, use_container_width=True)
                        
                        # Métricas del autor
                        author_total = author_historical['pageviews'].sum()
                        author_avg = author_historical['pageviews'].mean()
                        author_articles = len(author_data['url_normalized'].unique())
                        
                        col_auth1, col_auth2, col_auth3 = st.columns(3)
                        with col_auth1:
                            st.metric("📊 Total Pageviews", f"{author_total:,.0f}")
                        with col_auth2:
                            st.metric("📈 Promedio por Período", f"{author_avg:,.0f}")
                        with col_auth3:
                            st.metric("📝 Artículos", f"{author_articles:,}")
                        
                        # Comparación con el total
                        if total_pageviews_period > 0:
                            author_percentage = (author_total / total_pageviews_period) * 100
                            st.info(f"📊 **{selected_author}** representa el **{author_percentage:.1f}%** del tráfico total en este período")
                    else:
                        st.warning(f"No hay datos históricos para {selected_author}")
                else:
                    st.info("No hay información de autores disponible para mostrar el histórico por autor")
            
            else:
                st.error("❌ No se pudieron cargar los datos históricos")
    
    elif ga4_df is not None and not ga4_df.empty:
        # Solo datos de GA4
        st.warning("⚠️ No se encontraron URLs de Clarín en el Google Sheet. Mostrando solo datos de GA4.")
        
        # Métricas de GA4
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("📊 Sesiones", f"{ga4_df['sessions'].sum():,.0f}")
        with col2:
            st.metric("👥 Usuarios", f"{ga4_df['totalUsers'].sum():,.0f}")
        with col3:
            st.metric("👁️ Vistas", f"{ga4_df['screenPageViews'].sum():,.0f}")
        with col4:
            st.metric("📉 Rebote", f"{ga4_df['bounceRate'].mean():.1f}%")
        
        st.markdown("---")
        st.subheader("Datos de Google Analytics 4")
        st.dataframe(ga4_df, use_container_width=True)
    
    else:
        # Solo datos del Sheet
        st.warning("⚠️ No se pudieron obtener datos de GA4. Mostrando solo datos del Google Sheet.")
        st.dataframe(sheets_filtered, use_container_width=True)

# Footer
st.markdown("---")
st.caption(f"📊 Dashboard de {media_config['name']} | Property ID: {media_config['property_id']} | Dominio: {media_config['domain']}")