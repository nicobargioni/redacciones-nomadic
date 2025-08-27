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
    normalize_url
,
    check_login
)

# Configuración de la página
st.set_page_config(
    page_title="Dashboard OK Diario",
    page_icon="🗞️",
    layout="wide"
)

# Verificar login antes de mostrar contenido
if not check_login():
    st.stop()

# Obtener configuración del medio
media_config = create_media_config()['okdiario']

st.title(f"{media_config['icon']} Dashboard de {media_config['name']}")
st.markdown("---")

# Sidebar con opciones
st.sidebar.header("⚙️ Configuración")

# Selector de rango de fechas para GA4
date_option = st.sidebar.selectbox(
    "Tipo de rango de fechas:",
    ["Preestablecido", "Personalizado"],
    key="date_option_okdiario"
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
        key="preset_range_okdiario"
    )
    start_date_param = date_range
    end_date_param = "today"
else:
    col1, col2 = st.sidebar.columns(2)
    with col1:
        start_date_custom = st.date_input(
            "Fecha inicio:",
            value=datetime.now() - timedelta(days=7),
            key="start_date_okdiario"
        )
    with col2:
        end_date_custom = st.date_input(
            "Fecha fin:",
            value=datetime.now(),
            key="end_date_okdiario"
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

# Usar archivo de credenciales correcto para OK Diario
credentials_file = "credentials_analytics_acceso_medios.json"

# Cargar datos
with st.spinner('Cargando datos...'):
    # Cargar datos del Google Sheet
    sheets_df = load_google_sheet_data()
    
    # Filtrar solo URLs de OK Diario
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
            key="author_filter_okdiario"
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
                    key="source_filter_okdiario",
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
                    key="medium_filter_okdiario",
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
        
        # Agregar columna url_normalized a ga4_filtered ANTES de aplicar filtros
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
        tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["📊 KPI", "📋 Datos", "📈 Análisis de Tráfico", "🔝 Top Páginas", "📉 Tendencias", "👤 Performance por Autor"])
        
        with tab1:
            st.subheader("📊 KPI Mensual - OK Diario")
            
            # Descripción del KPI
            st.markdown("""
            ### 🎯 Objetivo del Mes
            **Meta:** 3,000,000 de Page Views
            
            Este KPI mide el progreso hacia nuestro objetivo mensual de tráfico en artículos de OK Diario. 
            Se consideran únicamente las URLs registradas en el Google Sheet, proporcionando una vista específica del rendimiento editorial.
            """)
            
            # Configuración del KPI
            monthly_goal = 3000000  # 3 millones de Page Views
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
                    help="Page Views acumulados en lo que va del mes (solo artículos del Sheet)"
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
                title = {'text': "Progreso hacia Objetivo Mensual (Artículos del Sheet)"},
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
                file_name=f"okdiario_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
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
        
        with tab5:
            st.subheader("📈 Tendencias")
            
            # Usar ga4_filtered (ya filtrado por fuente/medio) para mostrar solo URLs que están en el Sheet
            if 'ga4_filtered' in locals() and ga4_filtered is not None and 'date' in ga4_filtered.columns and 'merged_df' in locals() and not merged_df.empty:
                # Obtener solo URLs normalizadas que están en el Sheet
                sheet_urls = set(merged_df['url_normalized'].dropna())
                ga4_for_trends = ga4_filtered[ga4_filtered['url_normalized'].isin(sheet_urls)].copy()
                
                if not ga4_for_trends.empty:
                    # Filtrar por el rango de fechas seleccionado
                    from datetime import datetime, timedelta
                    
                    # Calcular fechas de inicio y fin
                    today = datetime.now()
                    if date_option == "Preestablecido":
                        days_map = {
                            "7daysAgo": 7,
                            "14daysAgo": 14, 
                            "30daysAgo": 30,
                            "90daysAgo": 90
                        }
                        days_back = days_map.get(date_range, 7)
                        start_date = today - timedelta(days=days_back)
                    else:
                        # Para fechas personalizadas, usar la fecha de inicio seleccionada
                        start_date = pd.to_datetime(start_date_custom)
                    
                    # Filtrar ga4_for_trends por fechas
                    ga4_for_trends['date_parsed'] = pd.to_datetime(ga4_for_trends['date'])
                    ga4_trends_filtered = ga4_for_trends[
                        ga4_for_trends['date_parsed'] >= start_date
                    ].copy()
                    
                    if not ga4_trends_filtered.empty:
                        # Tendencia diaria (solo URLs del Sheet en el rango seleccionado)
                        daily_metrics = ga4_trends_filtered.groupby('date').agg({
                            'sessions': 'sum',
                            'totalUsers': 'sum',
                            'screenPageViews': 'sum'
                        }).reset_index()
                    else:
                        daily_metrics = pd.DataFrame()
                    
                    # Mostrar gráficos solo si hay datos
                    if not daily_metrics.empty:
                        # Gráfico de líneas
                        fig_trend = go.Figure()
                        
                        fig_trend.add_trace(go.Scatter(
                            x=daily_metrics['date'],
                            y=daily_metrics['sessions'],
                            mode='lines+markers',
                            name='Sesiones',
                            line=dict(color=media_config['color'])
                        ))
                        
                        fig_trend.add_trace(go.Scatter(
                            x=daily_metrics['date'],
                            y=daily_metrics['totalUsers'],
                            mode='lines+markers',
                            name='Usuarios',
                            line=dict(color='orange')
                        ))
                        
                        if date_option == "Preestablecido":
                            period_name = {
                                "7daysAgo": "7 días",
                                "14daysAgo": "14 días", 
                                "30daysAgo": "30 días",
                                "90daysAgo": "90 días"
                            }.get(date_range, "período seleccionado")
                        else:
                            period_name = f"{start_date_custom.strftime('%d/%m/%Y')} - {end_date_custom.strftime('%d/%m/%Y')}"
                        
                        fig_trend.update_layout(
                            title=f'Tendencia de Tráfico Diario - Últimos {period_name}',
                            xaxis_title='Fecha',
                            yaxis_title='Cantidad',
                            hovermode='x unified'
                        )
                        
                        st.plotly_chart(fig_trend, use_container_width=True)
                        
                        # Métricas por día de la semana (usando datos filtrados)
                        ga4_trends_filtered['dayOfWeek'] = pd.to_datetime(ga4_trends_filtered['date']).dt.day_name()
                        day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
                        
                        weekly_pattern = ga4_trends_filtered.groupby('dayOfWeek')['sessions'].sum().reindex(day_order)
                        
                        fig_weekly = px.bar(
                            x=weekly_pattern.index,
                            y=weekly_pattern.values,
                            title=f'Patrón Semanal de Tráfico - Últimos {period_name}',
                            labels={'x': 'Día de la Semana', 'y': 'Sesiones Totales'},
                            color_discrete_sequence=[media_config['color']]
                        )
                        st.plotly_chart(fig_weekly, use_container_width=True)
                    else:
                        period_display = period_name if date_option == "Preestablecido" else f"período {period_name}"
                        st.info(f"No hay datos de tendencias para el {period_display}")
                else:
                    st.info("No hay datos de tendencias para las URLs del Sheet")
            else:
                st.info("No hay datos de tendencias disponibles")
        
        with tab6:
            st.subheader("👤 Performance por Autor")
            
            if 'autor' in merged_df.columns and not merged_df.empty:
                # Calcular métricas por autor
                author_performance = merged_df.groupby('autor').agg({
                    'screenPageViews': 'sum',
                    'titulo': 'count',  # Contar notas
                    'sessions': 'sum',
                    'totalUsers': 'sum'
                }).reset_index()
                
                # Renombrar columnas
                author_performance = author_performance.rename(columns={
                    'titulo': 'Notas Redactadas',
                    'screenPageViews': 'Page Views',
                    'sessions': 'Sesiones',
                    'totalUsers': 'Usuarios'
                })
                
                # Ordenar por Page Views descendente
                author_performance = author_performance.sort_values('Page Views', ascending=False)
                
                # Mostrar métricas principales
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    total_authors = len(author_performance)
                    st.metric("📝 Total Autores", total_authors)
                
                with col2:
                    avg_pageviews = author_performance['Page Views'].mean()
                    st.metric("👁️ Page Views Promedio", f"{avg_pageviews:,.0f}")
                
                with col3:
                    avg_articles = author_performance['Notas Redactadas'].mean()
                    st.metric("📰 Notas Promedio", f"{avg_articles:.1f}")
                
                st.markdown("---")
                
                # Gráfico de Page Views por Autor (Top 15)
                top_authors_pv = author_performance.head(15)
                fig_pv = px.bar(
                    top_authors_pv,
                    x='Page Views',
                    y='autor',
                    orientation='h',
                    title='Top Autores por Page Views',
                    labels={'autor': 'Autor', 'Page Views': 'Page Views'},
                    color_discrete_sequence=[media_config['color']]
                )
                fig_pv.update_yaxes(autorange='reversed')
                st.plotly_chart(fig_pv, use_container_width=True)
                
                # Gráfico de Notas Redactadas por Autor (Top 15)
                top_authors_notes = author_performance.nlargest(15, 'Notas Redactadas')
                fig_notes = px.bar(
                    top_authors_notes,
                    x='Notas Redactadas',
                    y='autor',
                    orientation='h',
                    title='Top Autores por Notas Redactadas',
                    labels={'autor': 'Autor', 'Notas Redactadas': 'Cantidad de Notas'},
                    color_discrete_sequence=['#ff6b35']
                )
                fig_notes.update_yaxes(autorange='reversed')
                st.plotly_chart(fig_notes, use_container_width=True)
                
                # Gráfico de dispersión: Page Views vs Notas Redactadas
                fig_scatter = px.scatter(
                    author_performance,
                    x='Notas Redactadas',
                    y='Page Views',
                    title='Relación entre Notas Redactadas y Page Views',
                    labels={'Notas Redactadas': 'Cantidad de Notas', 'Page Views': 'Page Views'},
                    hover_data=['autor'],
                    color_discrete_sequence=[media_config['color']]
                )
                st.plotly_chart(fig_scatter, use_container_width=True)
                
                # Tabla detallada
                st.subheader("📊 Tabla Detallada por Autor")
                
                # Selector para ordenar
                sort_by = st.selectbox(
                    "Ordenar por:",
                    ['Page Views', 'Notas Redactadas', 'Sesiones', 'Usuarios'],
                    key="sort_authors_okdiario"
                )
                
                # Ordenar según selección
                author_display = author_performance.sort_values(sort_by, ascending=False)
                
                # Formatear números para mejor visualización
                author_display_formatted = author_display.copy()
                author_display_formatted['Page Views'] = author_display_formatted['Page Views'].apply(lambda x: f"{x:,.0f}")
                author_display_formatted['Sesiones'] = author_display_formatted['Sesiones'].apply(lambda x: f"{x:,.0f}")
                author_display_formatted['Usuarios'] = author_display_formatted['Usuarios'].apply(lambda x: f"{x:,.0f}")
                
                st.dataframe(author_display_formatted, use_container_width=True, height=400)
                
                # Descarga de datos de performance
                csv_performance = author_performance.to_csv(index=False)
                st.download_button(
                    label="📥 Descargar Performance por Autor",
                    data=csv_performance,
                    file_name=f"okdiario_performance_autores_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv"
                )
            else:
                st.info("No hay datos de autores disponibles para mostrar performance")
    
    elif ga4_df is not None and not ga4_df.empty:
        # Solo datos de GA4
        st.warning(f"⚠️ No se encontraron URLs de {media_config['name']} en el Google Sheet. Mostrando solo datos de GA4.")
        
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