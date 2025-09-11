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
    get_ga4_data_with_country,
    filter_media_urls,
    merge_sheets_with_ga4,
    create_media_config,
    normalize_url,
    check_login,
    get_ga4_growth_data,
    get_ga4_growth_data_custom
)

# Configuración de la página
st.set_page_config(
    page_title="Dashboard El Español - Cliente",
    page_icon="🇪🇸",
    layout="wide"
)

# Verificar login antes de mostrar contenido
if not check_login('elespanol', page_type='cliente'):
    st.stop()

# Obtener configuración del medio
media_config = create_media_config()['elespanol']

st.title(f"{media_config['icon']} Dashboard de {media_config['name']}")
st.markdown("---")

# Sidebar con opciones
st.sidebar.header("⚙️ Configuración")

# Selector de rango de fechas para GA4
date_option = st.sidebar.selectbox(
    "Tipo de rango de fechas:",
    ["Preestablecido", "Personalizado"],
    key="date_option_elespanol"
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
        key="preset_range_elespanol"
    )
    start_date_param = date_range
    end_date_param = "today"
else:
    col1, col2 = st.sidebar.columns(2)
    with col1:
        start_date_custom = st.date_input(
            "Fecha inicio:",
            value=datetime.now() - timedelta(days=7),
            key="start_date_elespanol"
        )
    with col2:
        end_date_custom = st.date_input(
            "Fecha fin:",
            value=datetime.now(),
            key="end_date_elespanol"
        )
    
    # Convertir fechas a formato GA4
    start_date_param = start_date_custom.strftime("%Y-%m-%d")
    end_date_param = end_date_custom.strftime("%Y-%m-%d")
    
    # Validar que la fecha de inicio sea anterior a la fecha de fin
    if start_date_custom > end_date_custom:
        st.sidebar.error("⚠️ La fecha de inicio debe ser anterior a la fecha de fin")
        start_date_param = "7daysAgo"
        end_date_param = "today"

# Filtro por país
st.sidebar.markdown("---")
st.sidebar.subheader("🌍 Filtro Geográfico")
country_filter = st.sidebar.selectbox(
    "Filtrar por país:",
    ["Todos los países", "United States", "Spain", "Argentina", "Mexico", "Colombia", "Chile", "Peru"],
    key="country_filter_elespanol",
    help="Filtra los datos de GA4 por país específico"
)

# Botón de actualización
if st.sidebar.button("🔄 Actualizar datos"):
    st.cache_data.clear()
    st.rerun()

# Usar archivo de credenciales (por defecto usa medios, cambiar si es necesario)
credentials_file = "credentials_analytics_acceso_medios.json"

# Cargar datos
with st.spinner('Cargando datos...'):
    # Cargar datos del Google Sheet
    sheets_df = load_google_sheet_data()
    
    # Filtrar solo URLs de El Español
    if sheets_df is not None:
        sheets_filtered = filter_media_urls(sheets_df, media_config['domain'])
    else:
        sheets_filtered = pd.DataFrame()
    
    # Cargar datos de GA4 con o sin filtro de país
    if country_filter != "Todos los países":
        ga4_df = get_ga4_data_with_country(
            media_config['property_id'],
            credentials_file,
            start_date=start_date_param,
            end_date=end_date_param,
            country_filter=country_filter
        )
    else:
        ga4_df = get_ga4_data(
            media_config['property_id'],
            credentials_file,
            start_date=start_date_param,
            end_date=end_date_param
        )

# Verificar si hay datos en el Sheet
if sheets_filtered.empty:
    st.warning("📝 Sin notas en sheets de control")
    st.info(f"""
    **Estado actual:**
    - No hay URLs de {media_config['domain']} registradas en el Google Sheet de control
    - Para ver el dashboard completo, es necesario agregar artículos de {media_config['name']} al Google Sheet
    """)
    
    # Mostrar solo datos de GA4 si están disponibles
    if ga4_df is not None and not ga4_df.empty:
        st.subheader("📊 Datos disponibles de Google Analytics 4")
        
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
        st.dataframe(ga4_df, use_container_width=True)
    else:
        st.info("No hay datos de Google Analytics 4 disponibles para mostrar.")

elif ga4_df is None or ga4_df.empty:
    st.error("⚠️ No se encontraron datos de Google Analytics 4")
    st.info(f"""
    **Posibles causas:**
    - Error al conectar con Google Analytics 4
    - Credenciales incorrectas o sin permisos para la propiedad {media_config['property_id']}
    - Property ID no configurado correctamente
    - No hay datos para el país seleccionado: {country_filter}
    """)
    
    # Mostrar solo datos del Sheet
    st.subheader("📋 Datos del Google Sheet")
    st.dataframe(sheets_filtered, use_container_width=True)

else:
    # Agregar filtro por autor si hay datos
    author_filter = None
    if not sheets_filtered.empty and 'autor' in sheets_filtered.columns:
        authors = sorted(sheets_filtered['autor'].dropna().unique())
        author_filter = st.sidebar.multiselect(
            "👤 Filtrar por Autor:",
            options=authors,
            default=None,
            key="author_filter_elespanol"
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
                    key="source_filter_elespanol",
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
                    key="medium_filter_elespanol",
                    help="Medio del tráfico (organic, cpc, referral, etc.)"
                )
    
    # Métricas de datos cargados
    st.sidebar.markdown("---")
    st.sidebar.metric("URLs en Sheet", len(sheets_filtered) if not sheets_filtered.empty else 0)
    if ga4_df is not None:
        st.sidebar.metric("Páginas en GA4", ga4_df['pagePath'].nunique())
    else:
        st.sidebar.metric("Páginas en GA4", 0)
    
    if country_filter != "Todos los países":
        st.sidebar.success(f"🌍 Filtrado por: {country_filter}")
    
    # Mergear datos si ambos están disponibles
    if not sheets_filtered.empty and ga4_df is not None and not ga4_df.empty:
        # Aplicar filtros de fuente y medio a GA4 antes del merge
        ga4_filtered = ga4_df.copy()
        
        # Agregar columna url_normalized a ga4_filtered para uso posterior
        ga4_filtered['url_normalized'] = ga4_filtered['pagePath'].apply(
            lambda x: normalize_url(f"{media_config['domain']}{x}")
        )
        
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
        
        # Métricas principales
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            total_sessions = merged_df['sessions'].sum() if 'sessions' in merged_df.columns else 0
            st.metric("📊 Sesiones Totales", f"{total_sessions:,.0f}")
        
        with col2:
            total_users = merged_df['totalUsers'].sum() if 'totalUsers' in merged_df.columns else 0
            st.metric("👥 Usuarios Totales", f"{total_users:,.0f}")
        
        with col3:
            total_pageviews = merged_df['screenPageViews'].sum() if 'screenPageViews' in merged_df.columns else 0
            st.metric("👁️ Vistas de Página", f"{total_pageviews:,.0f}")
        
        with col4:
            avg_bounce = merged_df['bounceRate'].mean() if 'bounceRate' in merged_df.columns else 0
            st.metric("📉 Tasa de Rebote Promedio", f"{avg_bounce:.1f}%")
        
        st.markdown("---")
        
        # Obtener datos de GA4 para KPI (solo URLs del Sheet del mes actual)
        from datetime import datetime
        current_month_start = datetime.now().replace(day=1).strftime('%Y-%m-%d')
        current_month_today = datetime.now().strftime('%Y-%m-%d')
        
        # Si hay filtro de país, aplicarlo también al KPI mensual
        if country_filter != "Todos los países":
            ga4_monthly_df = get_ga4_data_with_country(
                media_config['property_id'],
                credentials_file,
                start_date=current_month_start,
                end_date=current_month_today,
                country_filter=country_filter
            )
        else:
            ga4_monthly_df = get_ga4_data(
                media_config['property_id'],
                credentials_file,
                start_date=current_month_start,
                end_date=current_month_today
            )
        
        # Calcular Page Views solo de URLs que están en el Sheet
        total_monthly_pageviews = 0
        if ga4_monthly_df is not None and not ga4_monthly_df.empty and not sheets_filtered.empty:
            # Mergear GA4 mensual con URLs del Sheet para obtener solo artículos registrados
            merged_monthly = merge_sheets_with_ga4(sheets_filtered, ga4_monthly_df, media_config['domain'])
            if not merged_monthly.empty and 'screenPageViews' in merged_monthly.columns:
                total_monthly_pageviews = merged_monthly['screenPageViews'].sum()
        
        # Tabs para diferentes vistas
        tab1, tab2, tab3, tab4 = st.tabs(["📊 KPI", "📋 Datos", "🔝 Top Páginas", "📈 Crecimiento"])
        
        with tab1:
            if country_filter != "Todos los países":
                st.subheader(f"📊 KPI Mensual - {media_config['name']} ({country_filter})")
            else:
                st.subheader(f"📊 KPI Mensual - {media_config['name']}")
            
            # Descripción del KPI
            st.markdown(f"""
            ### 🎯 Objetivo del Mes
            **Meta:** 2,000,000 de Page Views{' desde ' + country_filter if country_filter != "Todos los países" else ''}
            
            Este KPI mide el progreso hacia nuestro objetivo mensual de tráfico en artículos de {media_config['name']}. 
            Se consideran únicamente las URLs registradas en el Google Sheet{', filtrando por ' + country_filter if country_filter != "Todos los países" else ''}.
            """)
            
            # Configuración del KPI
            monthly_goal = 2000000  # 2 millones de Page Views
            current_progress = total_monthly_pageviews
            progress_percentage = (current_progress / monthly_goal) * 100 if monthly_goal > 0 else 0
            
            # Métricas principales del KPI
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric(
                    "🎯 Objetivo Mensual", 
                    f"{monthly_goal:,}",
                    help="Meta de Page Views para este mes"
                )
            
            with col2:
                st.metric(
                    "📈 Progreso Actual", 
                    f"{current_progress:,}",
                    delta=f"{current_progress - monthly_goal:,}" if current_progress >= monthly_goal else None,
                    help=f"Page Views acumulados en lo que va del mes{' desde ' + country_filter if country_filter != 'Todos los países' else ''}"
                )
            
            with col3:
                st.metric(
                    "📊 % Completado", 
                    f"{progress_percentage:.1f}%",
                    help="Porcentaje del objetivo alcanzado"
                )
            
            # Gráfico de progreso
            st.markdown("---")
            
            # Crear gráfico de gauge/progreso
            import plotly.graph_objects as go
            
            fig = go.Figure(go.Indicator(
                mode = "gauge+number+delta",
                value = current_progress,
                domain = {'x': [0, 1], 'y': [0, 1]},
                title = {'text': f"Progreso hacia Objetivo Mensual{' - ' + country_filter if country_filter != 'Todos los países' else ''}"},
                delta = {'reference': monthly_goal, 'valueformat': ',.0f'},
                gauge = {
                    'axis': {'range': [None, monthly_goal * 1.2]},
                    'bar': {'color': media_config['color']},
                    'steps': [
                        {'range': [0, monthly_goal * 0.5], 'color': "lightgray"},
                        {'range': [monthly_goal * 0.5, monthly_goal * 0.8], 'color': "yellow"},
                        {'range': [monthly_goal * 0.8, monthly_goal], 'color': "lightgreen"}
                    ],
                    'threshold': {
                        'line': {'color': "red", 'width': 4},
                        'thickness': 0.75,
                        'value': monthly_goal
                    }
                }
            ))
            
            fig.update_layout(
                height=400,
                font={'color': "darkblue", 'family': "Arial"}
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Información adicional
            current_date = datetime.now()
            days_in_month = current_date.day
            
            # Calcular días totales del mes actual
            if current_date.month == 12:
                next_month = current_date.replace(year=current_date.year + 1, month=1, day=1)
            else:
                next_month = current_date.replace(month=current_date.month + 1, day=1)
            
            days_total_month = (next_month - timedelta(days=1)).day
            daily_average = current_progress / days_in_month if days_in_month > 0 else 0
            projected_monthly = daily_average * days_total_month
            
            st.markdown("### 📈 Análisis de Tendencia")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric(
                    "📅 Días Transcurridos", 
                    f"{days_in_month}/{days_total_month}",
                    help="Días transcurridos del mes actual"
                )
            
            with col2:
                st.metric(
                    "📊 Promedio Diario", 
                    f"{daily_average:,.0f}",
                    help="Page Views promedio por día en lo que va del mes"
                )
            
            with col3:
                projection_delta = projected_monthly - monthly_goal
                st.metric(
                    "🔮 Proyección Mensual", 
                    f"{projected_monthly:,.0f}",
                    delta=f"{projection_delta:,.0f}",
                    delta_color="normal" if projection_delta >= 0 else "inverse",
                    help="Estimación de Page Views al final del mes según tendencia actual"
                )
            
            # Disclaimer sobre el cálculo de proyección
            st.markdown("---")
            st.info(f"""
            **📋 Metodología de Proyección:**
            
            • **Promedio Diario**: {daily_average:,.0f} Page Views (total acumulado ÷ {days_in_month} días transcurridos)
            
            • **Fórmula**: Promedio Diario × {days_total_month} días del mes = {projected_monthly:,.0f} Page Views proyectados
            
            {f'• **Filtro Geográfico**: Solo se consideran Page Views desde {country_filter}' if country_filter != "Todos los países" else '• **Sin filtro geográfico**: Se consideran Page Views de todos los países'}
            
            • **Consideraciones**: Esta proyección asume que el ritmo de publicación y engagement se mantiene constante. 
            Los fines de semana, feriados, eventos especiales o cambios en la estrategia editorial pueden afectar el resultado final.
            
            • **Solo URLs del Sheet**: Se consideran únicamente los artículos registrados en el Google Sheet, no todo el tráfico del sitio.
            """)
        
        with tab2:
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
                file_name=f"elespanol_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
        
        with tab3:
            st.subheader("📊 Análisis de Tráfico")
            
            # Top 10 páginas por sesiones
            if 'sessions' in merged_df.columns:
                top_pages = merged_df.nlargest(10, 'sessions')[['url_normalized', 'sessions']]
                fig_sessions = px.bar(
                    top_pages,
                    x='sessions',
                    y='url_normalized',
                    orientation='h',
                    title='Top 10 Páginas por Sesiones',
                    labels={'url_normalized': 'URL', 'sessions': 'Sesiones'},
                    color_discrete_sequence=[media_config['color']]
                )
                fig_sessions.update_yaxes(tickmode='linear', autorange='reversed')
                st.plotly_chart(fig_sessions, use_container_width=True)
            
            # Distribución de métricas de engagement
            if all(col in merged_df.columns for col in ['bounceRate', 'engagementRate']):
                metrics_data = {
                    'Métrica': ['Tasa de Rebote', 'Tasa de Engagement'],
                    'Promedio': [
                        merged_df['bounceRate'].mean(),
                        merged_df['engagementRate'].mean()
                    ]
                }
                fig_metrics = px.bar(
                    metrics_data,
                    x='Métrica',
                    y='Promedio',
                    title='Métricas de Engagement',
                    color_discrete_sequence=[media_config['color']]
                )
                st.plotly_chart(fig_metrics, use_container_width=True)
            
            # Correlación entre métricas
            if 'sessions' in merged_df.columns and 'screenPageViews' in merged_df.columns and not merged_df.empty:
                correlation_data = merged_df[merged_df['sessions'] > 0]
                if not correlation_data.empty:
                    st.subheader("🔄 Correlación Sesiones vs Vistas")
                    fig_scatter = px.scatter(
                        correlation_data,
                        x='sessions',
                        y='screenPageViews',
                        title='Relación entre Sesiones y Vistas de Página',
                        labels={'sessions': 'Sesiones', 'screenPageViews': 'Vistas de Página'},
                        color_discrete_sequence=[media_config['color']],
                        hover_data=['url_normalized'] if 'url_normalized' in correlation_data.columns else None
                    )
                    st.plotly_chart(fig_scatter, use_container_width=True)
                else:
                    st.info("No hay datos suficientes para mostrar la correlación")
        
        with tab4:
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
                    key="comparison_type_elespanol"
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
                        key="growth_current_start_elespanol"
                    )
                with col2:
                    current_end = st.date_input(
                        "Fin actual:",
                        value=datetime.now(),
                        key="growth_current_end_elespanol"
                    )
                
                st.markdown("**Período de Comparación:**")
                col3, col4 = st.columns(2)
                with col3:
                    previous_start = st.date_input(
                        "Inicio comparación:",
                        value=datetime.now() - timedelta(days=14),
                        key="growth_previous_start_elespanol"
                    )
                with col4:
                    previous_end = st.date_input(
                        "Fin comparación:",
                        value=datetime.now() - timedelta(days=8),
                        key="growth_previous_end_elespanol"
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
                    delta_color = "normal" if growth_pct >= 0 else "inverse"
                    st.metric(
                        "📊 Page Views",
                        f"{pv_data['current']:,}",
                        delta=f"{growth_pct:+.1f}% ({pv_data['growth_absolute']:+,})",
                        delta_color=delta_color
                    )
                
                with col2:
                    sessions_data = growth_data['data']['sessions']
                    growth_pct = sessions_data['growth_percentage']
                    delta_color = "normal" if growth_pct >= 0 else "inverse"
                    st.metric(
                        "👥 Sesiones",
                        f"{sessions_data['current']:,}",
                        delta=f"{growth_pct:+.1f}% ({sessions_data['growth_absolute']:+,})",
                        delta_color=delta_color
                    )
                
                with col3:
                    users_data = growth_data['data']['users']
                    growth_pct = users_data['growth_percentage']
                    delta_color = "normal" if growth_pct >= 0 else "inverse"
                    st.metric(
                        "🔗 Usuarios",
                        f"{users_data['current']:,}",
                        delta=f"{growth_pct:+.1f}% ({users_data['growth_absolute']:+,})",
                        delta_color=delta_color
                    )
                
                st.markdown("---")
                
                # Gráfico de comparación
                metrics = ['pageviews', 'sessions', 'users']
                metric_names = ['Page Views', 'Sesiones', 'Usuarios']
                current_values = [growth_data['data'][m]['current'] for m in metrics]
                previous_values = [growth_data['data'][m]['previous'] for m in metrics]
                
                # Crear DataFrame para el gráfico
                import pandas as pd
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

# Footer
st.markdown("---")
st.caption(f"📊 Dashboard de {media_config['name']} | Property ID: {media_config['property_id']} | Dominio: {media_config['domain']}")