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
    normalize_url,
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
    page_title="Dashboard OK Diario - Cliente",
    page_icon="🗞️",
    layout="wide"
)

# Ocultar sidebar
st.markdown("""
    <style>
    [data-testid="stSidebar"] {
        display: none !important;
    }
    section[data-testid="stSidebar"] {
        display: none !important;
    }
    </style>
""", unsafe_allow_html=True)

# Aplicar fuente Montserrat
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@300;400;500;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Montserrat', sans-serif !important;
}

h1, h2, h3, h4, h5, h6 {
    font-family: 'Montserrat', sans-serif !important;
    font-weight: 600;
}

.stMetric label {
    font-family: 'Montserrat', sans-serif !important;
    font-weight: 500;
}

.stMetric [data-testid="stMetricValue"] {
    font-family: 'Montserrat', sans-serif !important;
    font-weight: 600;
}

div[data-testid="stSidebarContent"] {
    font-family: 'Montserrat', sans-serif !important;
}

div[data-testid="stSidebarContent"] * {
    font-family: 'Montserrat', sans-serif !important;
}

.stButton button {
    font-family: 'Montserrat', sans-serif !important;
    font-weight: 500;
}

.stSelectbox, .stMultiSelect, .stSlider, .stDateInput {
    font-family: 'Montserrat', sans-serif !important;
}

p, span, div, label, input, textarea {
    font-family: 'Montserrat', sans-serif !important;
}

/* NO aplicar a íconos de Material Design */
.material-icons, [class*="material-symbols"] {
    font-family: 'Material Symbols Outlined' !important;
}
</style>
""", unsafe_allow_html=True)

# Verificar login antes de mostrar contenido
if not check_login('okdiario', page_type='cliente'):
    st.stop()

# Obtener configuración del medio
media_config = create_media_config()['okdiario']

st.title(f"{media_config['name']}")
st.markdown("---")

# Sidebar con opciones
st.sidebar.header("Configuración")

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
        st.sidebar.error("La fecha de inicio debe ser anterior a la fecha de fin")
        start_date_param = "7daysAgo"
        end_date_param = "today"

# Botón de actualización
if st.sidebar.button("Actualizar datos"):
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
    st.error("No se encontraron datos para mostrar")
    st.info(f"""
    **Posibles causas:**
    - No hay URLs de {media_config['domain']} en el Google Sheet
    - Error al conectar con Google Analytics 4
    - Credenciales incorrectas o sin permisos para la propiedad {media_config['property_id']}
    """)
else:
    # Métricas de datos cargados
    st.sidebar.metric("URLs en Sheet", len(sheets_filtered) if not sheets_filtered.empty else 0)
    if ga4_df is not None:
        st.sidebar.metric("Páginas en GA4", ga4_df['pagePath'].nunique())
    else:
        st.sidebar.metric("Páginas en GA4", 0)

    # Mergear datos si ambos están disponibles
    if not sheets_filtered.empty and ga4_df is not None and not ga4_df.empty:
        merged_df = merge_sheets_with_ga4(sheets_filtered, ga4_df, media_config['domain'])

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

        # ==================== SECCIÓN 1: GAUGE ====================


        # Configuración del KPI
        monthly_goal = 3000000  # 3 millones de Page Views
        current_progress = total_monthly_pageviews
        progress_percentage = (current_progress / monthly_goal) * 100 if monthly_goal > 0 else 0

        # Métricas principales del KPI
        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric(
                "Objetivo Mensual",
                f"{monthly_goal:,}",
                help="Meta de Page Views para este mes"
            )

        with col2:
            st.metric(
                "Progreso Actual",
                f"{current_progress:,}",
                delta=f"{current_progress - monthly_goal:,}" if current_progress >= monthly_goal else None,
                help="Page Views acumulados en lo que va del mes (solo artículos del Sheet)"
            )

        with col3:
            st.metric(
                "% Completado",
                f"{progress_percentage:.1f}%",
                help="Porcentaje del objetivo alcanzado"
            )

        # Crear gráfico de gauge/progreso
        import plotly.graph_objects as go

        fig = go.Figure(go.Indicator(
            mode = "gauge+number+delta",
            value = current_progress,
            domain = {'x': [0, 1], 'y': [0, 1]},
            title = {'text': "Progreso hacia Objetivo Mensual (Artículos del Sheet)"},
            delta = {'reference': monthly_goal, 'valueformat': ',.0f'},
            gauge = {
                'axis': {'range': [None, monthly_goal]},
                'bar': {'color': media_config['color']},
                'steps': [],
                'threshold': {
                    'line': {'color': "#9b51e0", 'width': 4},
                    'thickness': 0.75,
                    'value': monthly_goal
                }
            }
        ))

        fig.update_layout(
            height=400,
            font={'color': "darkblue", 'family': "Montserrat"}
        )

        st.plotly_chart(fig, use_container_width=True)

        st.markdown("---")

        # ==================== SECCIÓN 2: PROGRESIÓN DEL OBJETIVO ====================
        st.markdown("## Progresión del Objetivo a lo largo del Mes")

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

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric(
                "Días Transcurridos",
                f"{days_in_month}/{days_total_month}",
                help="Días transcurridos del mes actual"
            )

        with col2:
            st.metric(
                "Promedio Diario",
                f"{daily_average:,.0f}",
                help="Page Views promedio por día en lo que va del mes"
            )

        with col3:
            projection_delta = projected_monthly - monthly_goal
            st.metric(
                "Proyección Mensual",
                f"{projected_monthly:,.0f}",
                delta=f"{projection_delta:,.0f}",
                delta_color="normal",
                help="Estimación de Page Views al final del mes según tendencia actual"
            )

        # Obtener URLs del Sheet para filtrar datos históricos
        sheets_urls = None
        if not sheets_filtered.empty and 'url_normalized' in sheets_filtered.columns:
            sheets_urls = sheets_filtered['url_normalized'].dropna().unique().tolist()

        # Cargar datos históricos del mes actual para mostrar progresión
        with st.spinner("Cargando progresión del mes..."):
            hist_start_date = current_date.replace(day=1)
            hist_end_date = current_date

            historical_df = get_ga4_historical_data(
                media_config['property_id'],
                credentials_file,
                hist_start_date,
                hist_end_date,
                "day",
                sheets_urls,
                media_config['domain']
            )

        if historical_df is not None and not historical_df.empty:
            # Agrupar por día y sumar pageviews
            daily_progression = historical_df.groupby('period')['pageviews'].sum().reset_index()
            daily_progression = daily_progression.sort_values('period')

            # Calcular progresión acumulada
            daily_progression['cumulative_pageviews'] = daily_progression['pageviews'].cumsum()

            # Crear línea de objetivo (crecimiento lineal)
            daily_progression['goal_line'] = (monthly_goal / days_total_month) * daily_progression.index.to_series().apply(lambda x: x + 1)

            # Gráfico de progresión
            fig_progression = go.Figure()

            # Línea de progreso real
            fig_progression.add_trace(go.Scatter(
                x=daily_progression['period'],
                y=daily_progression['cumulative_pageviews'],
                mode='lines+markers',
                name='Progreso Real',
                line=dict(color=media_config['color'], width=3),
                marker=dict(size=6)
            ))

            # Línea de objetivo
            fig_progression.add_trace(go.Scatter(
                x=daily_progression['period'],
                y=daily_progression['goal_line'],
                mode='lines',
                name='Objetivo Lineal',
                line=dict(color='#9b51e0', width=2, dash='dash')
            ))

            fig_progression.update_layout(
                xaxis_title='Fecha',
                yaxis_title='Page Views Acumulados',
                hovermode='x unified',
                height=400
            )

            st.plotly_chart(fig_progression, use_container_width=True)
        else:
            st.warning("No se pudieron cargar los datos de progresión del mes")

        st.markdown("---")

        # ==================== SECCIÓN 3: TOP URLS ====================
        st.markdown("## Top URLs según Page Views")

        top_n = st.slider("Número de URLs a mostrar:", 5, 50, 20, key="top_urls_slider")

        if 'screenPageViews' in merged_df.columns:
            # Seleccionar columnas relevantes para mostrar
            display_columns = []
            if 'titulo' in merged_df.columns:
                display_columns.append('titulo')
            display_columns.extend(['url_normalized', 'screenPageViews'])

            top_urls = merged_df.nlargest(top_n, 'screenPageViews')[display_columns].copy()

            # Renombrar columnas
            column_rename = {
                'titulo': 'Título',
                'url_normalized': 'URL',
                'screenPageViews': 'Page Views'
            }
            top_urls = top_urls.rename(columns={k: v for k, v in column_rename.items() if k in top_urls.columns})

            # Gráfico de barras horizontales
            fig_top = go.Figure(data=[
                go.Bar(
                    y=top_urls['URL'][::-1],  # Invertir para mostrar el más alto arriba
                    x=top_urls['Page Views'][::-1],
                    orientation='h',
                    marker_color=media_config['color']
                )
            ])

            fig_top.update_layout(
                title=f'Top {top_n} URLs por Page Views',
                xaxis_title='Page Views',
                yaxis_title='URL',
                height=max(400, top_n * 20)
            )

            st.plotly_chart(fig_top, use_container_width=True)

            # Tabla de datos
            st.dataframe(
                top_urls.style.format({'Page Views': '{:,.0f}'}),
                use_container_width=True,
                hide_index=True
            )
        else:
            st.warning("No hay datos de Page Views disponibles")

        st.markdown("---")

        # ==================== SECCIÓN 4: COMPARATIVA DOMINIO VS SHEET ====================
        st.markdown("## Comparativa: Dominio Completo vs URLs del Sheet")
        st.caption(f"Período de análisis: {start_date_param} a {end_date_param}")

        # Obtener datos del dominio completo (sin home) usando el período seleccionado
        # Convertir el período al formato adecuado si es necesario
        if start_date_param.endswith("daysAgo"):
            days = int(start_date_param.replace("daysAgo", ""))
            period_start = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        else:
            period_start = start_date_param

        if end_date_param == "today":
            period_end = datetime.now().strftime('%Y-%m-%d')
        else:
            period_end = end_date_param

        # Usar los datos de GA4 ya cargados para la comparativa
        if ga4_df is not None and not ga4_df.empty:
            # Calcular métricas del dominio completo desde ga4_df
            domain_total_pv = ga4_df['screenPageViews'].sum()
            # Filtrar home page si existe
            ga4_no_home = ga4_df[~ga4_df['pagePath'].isin(['/', '/index.html', '/home'])]
            domain_no_home_pv = ga4_no_home['screenPageViews'].sum()
            domain_pages = ga4_no_home['pagePath'].nunique()

            pageviews_data = {
                'total_pageviews': domain_total_pv,
                'non_home_pageviews': domain_no_home_pv,
                'non_home_pages': domain_pages
            }
        else:
            pageviews_data = None

        if pageviews_data and 'screenPageViews' in merged_df.columns:
            # Métricas comparativas
            domain_total_pv = pageviews_data['total_pageviews']
            domain_no_home_pv = pageviews_data['non_home_pageviews']
            domain_pages = pageviews_data['non_home_pages']

            sheet_total_pv = merged_df['screenPageViews'].sum()
            sheet_pages = len(merged_df)

            col1, col2 = st.columns(2)

            with col1:
                st.markdown("### Dominio Completo (sin home)")
                st.metric("Total Page Views", f"{domain_no_home_pv:,.0f}")
                st.metric("Páginas Únicas", f"{domain_pages:,.0f}")
                avg_domain = domain_no_home_pv / domain_pages if domain_pages > 0 else 0
                st.metric("Promedio PV/Página", f"{avg_domain:,.0f}")

            with col2:
                st.markdown("### URLs del Sheet")
                st.metric("Total Page Views", f"{sheet_total_pv:,.0f}")
                st.metric("Páginas Únicas", f"{sheet_pages:,.0f}")
                avg_sheet = sheet_total_pv / sheet_pages if sheet_pages > 0 else 0
                st.metric("Promedio PV/Página", f"{avg_sheet:,.0f}")

            # Calcular porcentaje de representación
            if domain_no_home_pv > 0:
                representation_pct = (sheet_total_pv / domain_no_home_pv) * 100
                st.info(f"Las URLs del Sheet representan el **{representation_pct:.1f}%** del tráfico total del dominio (sin home)")

            # Gráfico comparativo
            comparison_data = pd.DataFrame({
                'Categoría': ['Dominio Completo\n(sin home)', 'URLs del Sheet'],
                'Total Page Views': [domain_no_home_pv, sheet_total_pv],
                'Promedio por Página': [avg_domain, avg_sheet]
            })

            col1, col2 = st.columns(2)

            with col1:
                # Gráfico de total
                fig_total = px.bar(
                    comparison_data,
                    x='Categoría',
                    y='Total Page Views',
                    title='Total Page Views: Dominio vs Sheet',
                    color='Categoría',
                    color_discrete_map={
                        'Dominio Completo\n(sin home)': '#808080',
                        'URLs del Sheet': media_config['color']
                    }
                )
                fig_total.update_layout(showlegend=False)
                st.plotly_chart(fig_total, use_container_width=True)

            with col2:
                # Gráfico de promedio
                fig_avg = px.bar(
                    comparison_data,
                    x='Categoría',
                    y='Promedio por Página',
                    title='Promedio Page Views por Página',
                    color='Categoría',
                    color_discrete_map={
                        'Dominio Completo\n(sin home)': '#808080',
                        'URLs del Sheet': media_config['color']
                    }
                )
                fig_avg.update_layout(showlegend=False)
                st.plotly_chart(fig_avg, use_container_width=True)
        else:
            st.error("No se pudieron obtener los datos comparativos")

        st.markdown("---")

        # ==================== SECCIÓN 5: CRECIMIENTO ====================
        st.markdown("## Análisis de Crecimiento")

        # Selector de tipo de comparación
        col1, col2 = st.columns([1, 3])

        with col1:
            comparison_type = st.selectbox(
                "Tipo de comparación:",
                ["day", "week", "month", "90days", "custom"],
                format_func=lambda x: {
                    "day": "Día actual vs día anterior",
                    "week": "Semana actual vs semana anterior",
                    "month": "Mes actual vs mes anterior",
                    "90days": "90 días actuales vs 90 días anteriores",
                    "custom": "Período personalizado"
                }[x],
                key="comparison_type_cliente_okdiario"
            )

        # Obtener URLs normalizadas del Sheet para filtrar
        sheets_urls_growth = None
        if not sheets_filtered.empty and 'url_normalized' in sheets_filtered.columns:
            sheets_urls_growth = sheets_filtered['url_normalized'].dropna().unique().tolist()

        # Si es personalizado, mostrar selectores de fecha
        if comparison_type == "custom":
            st.markdown("**Período Actual:**")
            col1, col2 = st.columns(2)
            with col1:
                current_start = st.date_input(
                    "Inicio actual:",
                    value=datetime.now() - timedelta(days=7),
                    key="growth_current_start_cliente_okdiario"
                )
            with col2:
                current_end = st.date_input(
                    "Fin actual:",
                    value=datetime.now(),
                    key="growth_current_end_cliente_okdiario"
                )

            st.markdown("**Período de Comparación:**")
            col3, col4 = st.columns(2)
            with col3:
                previous_start = st.date_input(
                    "Inicio comparación:",
                    value=datetime.now() - timedelta(days=14),
                    key="growth_previous_start_cliente_okdiario"
                )
            with col4:
                previous_end = st.date_input(
                    "Fin comparación:",
                    value=datetime.now() - timedelta(days=8),
                    key="growth_previous_end_cliente_okdiario"
                )

            # Obtener datos personalizados
            growth_data = get_ga4_growth_data_custom(
                media_config['property_id'],
                credentials_file,
                current_start,
                current_end,
                previous_start,
                previous_end,
                sheets_urls_growth
            )
        else:
            # Obtener datos predefinidos
            growth_data = get_ga4_growth_data(
                media_config['property_id'],
                credentials_file,
                comparison_type,
                sheets_urls_growth
            )

        if growth_data:
            

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
                delta_color = "normal"
                st.metric(
                    "Page Views",
                    f"{pv_data['current']:,}",
                    delta=format_growth_percentage(growth_pct, pv_data['growth_absolute']),
                    delta_color=delta_color
                )

            with col2:
                sessions_data = growth_data['data']['sessions']
                growth_pct = sessions_data['growth_percentage']
                delta_color = "normal"
                st.metric(
                    "Sesiones",
                    f"{sessions_data['current']:,}",
                    delta=format_growth_percentage(growth_pct, sessions_data['growth_absolute']),
                    delta_color=delta_color
                )

            with col3:
                users_data = growth_data['data']['users']
                growth_pct = users_data['growth_percentage']
                delta_color = "normal"
                st.metric(
                    "Usuarios",
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

        else:
            st.error("No se pudieron obtener los datos de crecimiento")

    elif ga4_df is not None and not ga4_df.empty:
        # Solo datos de GA4
        st.warning(f"No se encontraron URLs de {media_config['name']} en el Google Sheet. Mostrando solo datos de GA4.")

        # Métricas de GA4
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Sesiones", f"{ga4_df['sessions'].sum():,.0f}")
        with col2:
            st.metric("Usuarios", f"{ga4_df['totalUsers'].sum():,.0f}")
        with col3:
            st.metric("Vistas", f"{ga4_df['screenPageViews'].sum():,.0f}")
        with col4:
            st.metric("Rebote", f"{ga4_df['bounceRate'].mean():.1f}%")

        st.markdown("---")
        st.subheader("Datos de Google Analytics 4")
        st.dataframe(ga4_df, use_container_width=True)

    else:
        # Solo datos del Sheet
        st.warning("No se pudieron obtener datos de GA4. Mostrando solo datos del Google Sheet.")
        st.dataframe(sheets_filtered, use_container_width=True)

# Footer
st.markdown("---")
st.caption(f"Dashboard de {media_config['name']} | Property ID: {media_config['property_id']} | Dominio: {media_config['domain']}")
