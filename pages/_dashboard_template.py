"""
Template base para dashboards de medios.
Este módulo contiene toda la lógica compartida entre dashboards de redacción y cliente.
"""

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


def _apply_page_config(config):
    """Configurar página de Streamlit"""
    st.set_page_config(
        page_title=config['page_title'],
        page_icon=config.get('page_icon', '📰'),
        layout="wide"
    )


def _apply_styles():
    """Aplicar estilos CSS globales"""
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


def _check_authentication(config):
    """Verificar autenticación según configuración"""
    if not check_login(config['medio'], page_type=config['page_type']):
        st.stop()


def _render_sidebar_config(config):
    """Renderizar configuración en sidebar"""
    icon_prefix = "" if config['page_type'] == 'redaccion' else ""

    st.sidebar.header(f"{icon_prefix}Configuración")

    # Selector de rango de fechas para GA4
    date_option = st.sidebar.selectbox(
        "Tipo de rango de fechas:",
        ["Preestablecido", "Personalizado"],
        key=f"date_option_{config['medio']}"
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
            key=f"preset_range_{config['medio']}"
        )
        start_date_param = date_range
        end_date_param = "today"
    else:
        col1, col2 = st.sidebar.columns(2)
        with col1:
            start_date_custom = st.date_input(
                "Fecha inicio:",
                value=datetime.now() - timedelta(days=7),
                key=f"start_date_{config['medio']}"
            )
        with col2:
            end_date_custom = st.date_input(
                "Fecha fin:",
                value=datetime.now(),
                key=f"end_date_{config['medio']}"
            )

        # Convertir fechas a formato GA4
        start_date_param = start_date_custom.strftime("%Y-%m-%d")
        end_date_param = end_date_custom.strftime("%Y-%m-%d")

        # Validar que la fecha de inicio sea anterior a la fecha de fin
        if start_date_custom > end_date_custom:
            st.sidebar.error(f"{icon_prefix}La fecha de inicio debe ser anterior a la fecha de fin")
            start_date_param = "7daysAgo"
            end_date_param = "today"

    # Botón de actualización
    if st.sidebar.button(f"{icon_prefix}Actualizar datos"):
        st.cache_data.clear()
        st.rerun()

    return start_date_param, end_date_param


def _load_data(config, start_date_param, end_date_param):
    """Cargar datos de Google Sheets y GA4"""
    credentials_file = config.get('credentials_file', 'credentials_analytics_acceso_medios.json')

    with st.spinner('Cargando datos...'):
        # Cargar datos del Google Sheet
        sheets_df = load_google_sheet_data()

        # Filtrar solo URLs del medio
        if sheets_df is not None:
            sheets_filtered = filter_media_urls(sheets_df, config['domain'])
        else:
            sheets_filtered = pd.DataFrame()

        # Cargar datos de GA4
        ga4_df = get_ga4_data(
            config['property_id'],
            credentials_file,
            start_date=start_date_param,
            end_date=end_date_param
        )

    return sheets_filtered, ga4_df, credentials_file


def _render_gauge_section(config, total_monthly_pageviews):
    """Renderizar sección de gauge de objetivo mensual"""
    monthly_goal = config.get('monthly_goal', 3000000)
    current_progress = total_monthly_pageviews
    progress_percentage = (current_progress / monthly_goal) * 100 if monthly_goal > 0 else 0

    icon_prefix = "" if config['page_type'] == 'redaccion' else ""

    # Métricas principales del KPI
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            f"{icon_prefix}Objetivo Mensual",
            f"{monthly_goal:,}",
            help="Meta de Page Views para este mes"
        )

    with col2:
        st.metric(
            f"{icon_prefix}Progreso Actual",
            f"{current_progress:,}",
            delta=f"{current_progress - monthly_goal:,}" if current_progress >= monthly_goal else None,
            help="Page Views acumulados en lo que va del mes (solo artículos del Sheet)"
        )

    with col3:
        st.metric(
            f"{icon_prefix}% Completado",
            f"{progress_percentage:.1f}%",
            help="Porcentaje del objetivo alcanzado"
        )

    # Crear gráfico de gauge/progreso
    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=current_progress,
        domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': "Progreso hacia Objetivo Mensual (Artículos del Sheet)"},
        delta={'reference': monthly_goal, 'valueformat': ',.0f'},
        gauge={
            'axis': {'range': [None, monthly_goal]},
            'bar': {'color': config['color']},
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


def _render_progression_section(config, merged_df, credentials_file):
    """Renderizar sección de progresión del objetivo"""
    is_redaccion = config['page_type'] == 'redaccion'
    title = "##  Real vs Objetivo" if is_redaccion else "## Progresión del Objetivo a lo largo del Mes"
    icon_prefix = " " if is_redaccion else ""

    st.markdown(title)

    # Información adicional
    current_date = datetime.now()
    days_in_month = current_date.day

    # Calcular días totales del mes actual
    if current_date.month == 12:
        next_month = current_date.replace(year=current_date.year + 1, month=1, day=1)
    else:
        next_month = current_date.replace(month=current_date.month + 1, day=1)

    days_total_month = (next_month - timedelta(days=1)).day

    monthly_goal = config.get('monthly_goal', 3000000)

    # Calcular métricas
    sheets_urls = None
    if not merged_df.empty and 'url_normalized' in merged_df.columns:
        sheets_urls = merged_df['url_normalized'].dropna().unique().tolist()

    # Calcular progreso actual del mes
    current_month_start = datetime.now().replace(day=1).strftime('%Y-%m-%d')
    current_month_today = datetime.now().strftime('%Y-%m-%d')

    ga4_monthly_df = get_ga4_data(
        config['property_id'],
        credentials_file,
        start_date=current_month_start,
        end_date=current_month_today
    )

    total_monthly_pageviews = 0
    if ga4_monthly_df is not None and not ga4_monthly_df.empty:
        sheets_filtered = filter_media_urls(load_google_sheet_data(), config['domain'])
        merged_monthly = merge_sheets_with_ga4(sheets_filtered, ga4_monthly_df, config['domain'])
        if not merged_monthly.empty and 'screenPageViews' in merged_monthly.columns:
            total_monthly_pageviews = merged_monthly['screenPageViews'].sum()

    current_progress = total_monthly_pageviews
    daily_average = current_progress / days_in_month if days_in_month > 0 else 0
    projected_monthly = daily_average * days_total_month

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            f"{icon_prefix}Días Transcurridos",
            f"{days_in_month}/{days_total_month}",
            help="Días transcurridos del mes actual"
        )

    with col2:
        st.metric(
            f"{icon_prefix}Promedio Diario",
            f"{daily_average:,.0f}",
            help="Page Views promedio por día en lo que va del mes"
        )

    with col3:
        projection_delta = projected_monthly - monthly_goal
        st.metric(
            f"{icon_prefix}Proyección Mensual",
            f"{projected_monthly:,.0f}",
            delta=f"{projection_delta:,.0f}",
            delta_color="normal",
            help="Estimación de Page Views al final del mes según tendencia actual"
        )

    # Cargar datos históricos del mes actual para mostrar progresión
    with st.spinner("Cargando progresión del mes..."):
        hist_start_date = current_date.replace(day=1)
        hist_end_date = current_date

        historical_df = get_ga4_historical_data(
            config['property_id'],
            credentials_file,
            hist_start_date,
            hist_end_date,
            "day",
            sheets_urls,
            config['domain']
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
            line=dict(color=config['color'], width=3),
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
            height=400,
            showlegend=True if not is_redaccion else True
        )

        st.plotly_chart(fig_progression, use_container_width=True)
    else:
        st.warning("No se pudieron cargar los datos de progresión del mes")


def _render_author_performance(config, merged_df):
    """Renderizar sección de performance por autor (solo para redacción)"""
    if config['page_type'] != 'redaccion':
        return

    st.markdown("---")
    st.markdown("##  Performance por Autor | Mes en curso")

    if not merged_df.empty and 'autor' in merged_df.columns and 'screenPageViews' in merged_df.columns:
        # Filtrar datos del mes actual
        merged_df_monthly = merged_df.copy()
        if 'datePub' in merged_df_monthly.columns:
            merged_df_monthly['datePub_dt'] = pd.to_datetime(merged_df_monthly['datePub'], format='%d/%m/%Y', errors='coerce')
            current_month = datetime.now().month
            current_year = datetime.now().year
            merged_df_monthly = merged_df_monthly[
                (merged_df_monthly['datePub_dt'].dt.month == current_month) &
                (merged_df_monthly['datePub_dt'].dt.year == current_year)
            ]

        # Agrupar por autor y sumar pageviews del mes actual
        author_performance = merged_df_monthly.groupby('autor').agg({
            'screenPageViews': 'sum',
            'url_normalized': 'count'
        }).reset_index()

        author_performance.columns = ['Autor', 'Total Page Views', 'Cantidad de Artículos']
        author_performance['Promedio por Artículo'] = author_performance['Total Page Views'] / author_performance['Cantidad de Artículos']
        author_performance = author_performance.sort_values('Total Page Views', ascending=False)

        # Gráfico de barras por autor
        fig_authors = go.Figure(data=[
            go.Bar(
                x=author_performance['Autor'],
                y=author_performance['Total Page Views'],
                marker_color=config['color'],
                text=author_performance['Total Page Views'].apply(lambda x: f'{x:,.0f}'),
                textposition='outside'
            )
        ])

        fig_authors.update_layout(
            xaxis_title='Autor',
            yaxis_title='Page Views',
            height=400
        )

        st.plotly_chart(fig_authors, use_container_width=True)

        # Tabla de performance
        st.dataframe(
            author_performance.style.format({
                'Total Page Views': '{:,.0f}',
                'Promedio por Artículo': '{:,.0f}'
            }),
            use_container_width=True,
            hide_index=True
        )

        # ==================== SUBSECCIÓN: PERFORMANCE INDIVIDUAL POR AUTOR ====================
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("###  Performance Individual por Autor y Fecha")

        # Filtros
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            # Selector múltiple de autores
            authors_list = sorted(merged_df['autor'].dropna().unique())
            selected_authors = st.multiselect(
                "Seleccionar Autor(es):",
                options=authors_list,
                default=[authors_list[0]] if authors_list else [],
                key=f"individual_author_selector_{config['medio']}"
            )

        with col2:
            # Selector de fecha inicial
            if 'datePub' in merged_df.columns:
                min_date = pd.to_datetime(merged_df['datePub'], format='%d/%m/%Y', errors='coerce').min().date()
                max_date = pd.to_datetime(merged_df['datePub'], format='%d/%m/%Y', errors='coerce').max().date()
            else:
                min_date = datetime.now().date() - timedelta(days=30)
                max_date = datetime.now().date()

            start_date = st.date_input(
                "Fecha Inicial:",
                value=min_date,
                min_value=min_date,
                max_value=max_date,
                key=f"author_start_date_{config['medio']}"
            )

        with col3:
            # Selector de fecha final
            end_date = st.date_input(
                "Fecha Final:",
                value=max_date,
                min_value=min_date,
                max_value=max_date,
                key=f"author_end_date_{config['medio']}"
            )

        with col4:
            # Radio buttons para tipo de visualización
            data_view_type = st.radio(
                "Tipo de datos:",
                options=["Data por día", "Data mensualizada"],
                key=f"data_view_type_{config['medio']}"
            )

        if selected_authors:
            # Filtrar datos por autores seleccionados y fecha
            author_data = merged_df[merged_df['autor'].isin(selected_authors)].copy()

            if 'datePub' in author_data.columns:
                author_data['datePub'] = pd.to_datetime(author_data['datePub'], format='%d/%m/%Y', errors='coerce')
                author_data = author_data[
                    (author_data['datePub'].dt.date >= start_date) &
                    (author_data['datePub'].dt.date <= end_date)
                ]

            if not author_data.empty:
                # Métricas totales del período
                total_articles = len(author_data)
                total_views = author_data['screenPageViews'].sum() if 'screenPageViews' in author_data.columns else 0
                avg_views = total_views / total_articles if total_articles > 0 else 0

                # Mostrar métricas
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Artículos Publicados", f"{total_articles:,}")
                with col2:
                    st.metric("Total Page Views", f"{total_views:,.0f}")
                with col3:
                    st.metric("Promedio por Artículo", f"{avg_views:,.0f}")

                # Visualización según tipo seleccionado
                if data_view_type == "Data por día":
                    # Gráfico de líneas por día
                    if 'datePub' in author_data.columns and 'screenPageViews' in author_data.columns:
                        fig_author_time = go.Figure()

                        # Crear una traza por cada autor
                        colors = [config['color'], '#ff6b6b', '#4ecdc4', '#45b7d1', '#f9ca24', '#6c5ce7', '#a29bfe', '#fd79a8', '#fdcb6e']

                        for idx, author in enumerate(selected_authors):
                            author_specific_data = author_data[author_data['autor'] == author].copy()
                            daily_performance = author_specific_data.groupby(author_specific_data['datePub'].dt.date).agg({
                                'screenPageViews': 'sum',
                                'url_normalized': 'count'
                            }).reset_index()
                            daily_performance.columns = ['Fecha', 'Page Views', 'Artículos']
                            daily_performance = daily_performance.sort_values('Fecha')

                            fig_author_time.add_trace(go.Scatter(
                                x=daily_performance['Fecha'],
                                y=daily_performance['Page Views'],
                                mode='lines+markers',
                                name=author,
                                line=dict(color=colors[idx % len(colors)], width=2),
                                marker=dict(size=6),
                                hovertemplate=f'<b>{author}</b><br>%{{x}}<br>Page Views: %{{y:,.0f}}<extra></extra>'
                            ))

                        fig_author_time.update_layout(
                            xaxis_title='Fecha',
                            yaxis_title='Page Views',
                            hovermode='x unified',
                            height=400,
                            showlegend=True
                        )

                        st.plotly_chart(fig_author_time, use_container_width=True)

                else:  # Data mensualizada
                    # Gráfico de barras por mes
                    if 'datePub' in author_data.columns and 'screenPageViews' in author_data.columns:
                        # Agregar columna de mes-año
                        author_data['month_year'] = author_data['datePub'].dt.to_period('M').astype(str)

                        # Agrupar por autor y mes
                        monthly_performance = author_data.groupby(['autor', 'month_year']).agg({
                            'screenPageViews': 'sum',
                            'url_normalized': 'count'
                        }).reset_index()
                        monthly_performance.columns = ['Autor', 'Mes', 'Page Views', 'Artículos']

                        # Crear gráfico de barras agrupadas
                        fig_monthly = px.bar(
                            monthly_performance,
                            x='Mes',
                            y='Page Views',
                            color='Autor',
                            barmode='group',
                            text='Page Views'
                        )

                        fig_monthly.update_traces(texttemplate='%{text:,.0f}', textposition='outside')
                        fig_monthly.update_layout(
                            xaxis_title='Mes',
                            yaxis_title='Page Views',
                            height=400,
                            showlegend=True
                        )

                        st.plotly_chart(fig_monthly, use_container_width=True)

                        # Tabla de datos mensuales
                        st.markdown("#### Detalle Mensual por Autor")
                        pivot_table = monthly_performance.pivot(index='Mes', columns='Autor', values='Page Views').fillna(0)
                        st.dataframe(
                            pivot_table.style.format('{:,.0f}'),
                            use_container_width=True
                        )

                # Tabla de artículos individuales
                st.markdown("#### Artículos en el Período")
                display_cols = ['datePub', 'autor', 'titulo', 'screenPageViews'] if 'titulo' in author_data.columns else ['datePub', 'autor', 'url_normalized', 'screenPageViews']
                author_articles = author_data[display_cols].sort_values('screenPageViews', ascending=False)

                # Renombrar columnas
                rename_dict = {
                    'datePub': 'Fecha',
                    'autor': 'Autor',
                    'titulo': 'Título',
                    'url_normalized': 'URL',
                    'screenPageViews': 'Page Views'
                }
                author_articles = author_articles.rename(columns={k: v for k, v in rename_dict.items() if k in author_articles.columns})

                st.dataframe(
                    author_articles.style.format({
                        'Page Views': '{:,.0f}'
                    }),
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.warning(f"No hay datos para los autores seleccionados en el período")
        else:
            st.info("Selecciona al menos un autor para ver su performance")
    else:
        st.info("No hay datos de autores disponibles")


def _render_top_urls(config, merged_df, start_date_param, end_date_param):
    """Renderizar sección de top URLs"""
    st.markdown("---")

    is_redaccion = config['page_type'] == 'redaccion'
    icon_prefix = " " if is_redaccion else ""

    if is_redaccion:
        st.markdown(f"##{icon_prefix}Top URLs según Page Views")
        st.caption(f"Mostrando las 20 URLs con más pageviews del período seleccionado: {start_date_param} a {end_date_param}")
        top_n = 20
    else:
        st.markdown("## Top URLs según Page Views")
        top_n = st.slider("Número de URLs a mostrar:", 5, 50, 20, key=f"top_urls_slider_{config['medio']}")

    if 'screenPageViews' in merged_df.columns:
        # Seleccionar columnas relevantes para mostrar
        display_columns = []
        if 'titulo' in merged_df.columns:
            display_columns.append('titulo')
        display_columns.extend(['url_normalized', 'screenPageViews'])
        if 'autor' in merged_df.columns and is_redaccion:
            display_columns.append('autor')

        top_urls = merged_df.nlargest(top_n, 'screenPageViews')[display_columns].copy()

        # Renombrar columnas
        column_rename = {
            'titulo': 'Título',
            'url_normalized': 'URL',
            'screenPageViews': 'Page Views',
            'autor': 'Autor'
        }
        top_urls = top_urls.rename(columns={k: v for k, v in column_rename.items() if k in top_urls.columns})

        # Gráfico de barras horizontales
        fig_top = go.Figure(data=[
            go.Bar(
                y=top_urls['URL'][::-1],  # Invertir para mostrar el más alto arriba
                x=top_urls['Page Views'][::-1],
                orientation='h',
                marker_color=config['color']
            )
        ])

        fig_top.update_layout(
            title=f'Top {top_n} URLs por Page Views' if not is_redaccion else None,
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


def _render_domain_comparison(config, sheets_filtered, ga4_df, merged_df, credentials_file):
    """Renderizar sección de comparativa dominio vs sheet"""
    st.markdown("---")

    is_redaccion = config['page_type'] == 'redaccion'
    icon_prefix = " " if is_redaccion else ""

    st.markdown(f"##{icon_prefix}Comparativa: Dominio Completo vs URLs del Sheet")

    if is_redaccion:
        st.caption(f"Período de análisis: Mes en curso")
        # Obtener datos del mes en curso
        current_month_start_comp = datetime.now().replace(day=1).strftime('%Y-%m-%d')
        current_month_today_comp = datetime.now().strftime('%Y-%m-%d')
        comparison_start_param = current_month_start_comp
        comparison_end_param = current_month_today_comp
    else:
        # Selectores de tiempo para la comparativa
        col1, col2 = st.columns([1, 3])

        with col1:
            comparison_date_option = st.selectbox(
                "Rango de fechas:",
                ["7daysAgo", "14daysAgo", "30daysAgo", "90daysAgo", "Personalizado"],
                format_func=lambda x: {
                    "7daysAgo": "Últimos 7 días",
                    "14daysAgo": "Últimos 14 días",
                    "30daysAgo": "Últimos 30 días",
                    "90daysAgo": "Últimos 90 días",
                    "Personalizado": "Personalizado"
                }[x],
                key=f"comparison_date_range_{config['medio']}"
            )

        # Si es personalizado, mostrar selectores de fecha
        if comparison_date_option == "Personalizado":
            col1, col2 = st.columns(2)
            with col1:
                comparison_start_date = st.date_input(
                    "Fecha inicio:",
                    value=datetime.now() - timedelta(days=7),
                    key=f"comparison_start_{config['medio']}"
                )
            with col2:
                comparison_end_date = st.date_input(
                    "Fecha fin:",
                    value=datetime.now(),
                    key=f"comparison_end_{config['medio']}"
                )

            comparison_start_param = comparison_start_date.strftime("%Y-%m-%d")
            comparison_end_param = comparison_end_date.strftime("%Y-%m-%d")
        else:
            comparison_start_param = comparison_date_option
            comparison_end_param = "today"

        # Convertir el período al formato adecuado si es necesario
        if comparison_start_param.endswith("daysAgo"):
            days = int(comparison_start_param.replace("daysAgo", ""))
            period_start = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        else:
            period_start = comparison_start_param

        if comparison_end_param == "today":
            period_end = datetime.now().strftime('%Y-%m-%d')
        else:
            period_end = comparison_end_param

        st.caption(f"Período de análisis: {period_start} a {period_end}")

    # Cargar datos de GA4 para la comparativa
    with st.spinner('Cargando datos de comparativa...'):
        ga4_comparison_df = get_ga4_data(
            config['property_id'],
            credentials_file,
            start_date=comparison_start_param,
            end_date=comparison_end_param
        )

    # Usar los datos de GA4 de la comparativa
    if ga4_comparison_df is not None and not ga4_comparison_df.empty:
        # Mergear datos del Sheet con GA4 del período seleccionado
        merged_comparison_df = merge_sheets_with_ga4(sheets_filtered, ga4_comparison_df, config['domain'])

        # Calcular métricas del dominio completo
        domain_total_pv = ga4_comparison_df['screenPageViews'].sum()
        # Filtrar home page si existe
        ga4_no_home = ga4_comparison_df[~ga4_comparison_df['pagePath'].isin(['/', '/index.html', '/home'])]
        domain_no_home_pv = ga4_no_home['screenPageViews'].sum()
        domain_pages = ga4_no_home['pagePath'].nunique()

        pageviews_data = {
            'total_pageviews': domain_total_pv,
            'non_home_pageviews': domain_no_home_pv,
            'non_home_pages': domain_pages
        }
    else:
        pageviews_data = None
        merged_comparison_df = pd.DataFrame()

    if pageviews_data and not merged_comparison_df.empty and 'screenPageViews' in merged_comparison_df.columns:
        # Métricas comparativas
        domain_total_pv = pageviews_data['total_pageviews']
        domain_no_home_pv = pageviews_data['non_home_pageviews']
        domain_pages = pageviews_data['non_home_pages']

        sheet_total_pv = merged_comparison_df['screenPageViews'].sum()
        sheet_pages = len(merged_comparison_df)

        col1, col2 = st.columns(2)

        with col1:
            st.markdown(f"###{icon_prefix}Dominio Completo (sin home)")
            st.metric("Total Page Views", f"{domain_no_home_pv:,.0f}")
            st.metric("Páginas Únicas", f"{domain_pages:,.0f}")
            avg_domain = domain_no_home_pv / domain_pages if domain_pages > 0 else 0
            st.metric("Promedio PV/Página", f"{avg_domain:,.0f}")

        with col2:
            st.markdown(f"###{icon_prefix}URLs del Sheet")
            st.metric("Total Page Views", f"{sheet_total_pv:,.0f}")
            st.metric("Páginas Únicas", f"{sheet_pages:,.0f}")
            avg_sheet = sheet_total_pv / sheet_pages if sheet_pages > 0 else 0
            st.metric("Promedio PV/Página", f"{avg_sheet:,.0f}")

        # Calcular porcentaje de representación
        if domain_no_home_pv > 0:
            representation_pct = (sheet_total_pv / domain_no_home_pv) * 100
            st.info(f"{icon_prefix}Las URLs del Sheet representan el **{representation_pct:.1f}%** del tráfico total del dominio (sin home)")

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
                title='Total Page Views: Dominio vs Sheet' if not is_redaccion else None,
                color='Categoría',
                color_discrete_map={
                    'Dominio Completo\n(sin home)': '#808080',
                    'URLs del Sheet': config['color']
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
                title='Promedio Page Views por Página' if not is_redaccion else None,
                color='Categoría',
                color_discrete_map={
                    'Dominio Completo\n(sin home)': '#808080',
                    'URLs del Sheet': config['color']
                }
            )
            fig_avg.update_layout(showlegend=False)
            st.plotly_chart(fig_avg, use_container_width=True)
    else:
        st.error("No se pudieron obtener los datos comparativos")


def _render_growth_analysis(config, merged_df, credentials_file):
    """Renderizar sección de análisis de crecimiento"""
    st.markdown("---")

    is_redaccion = config['page_type'] == 'redaccion'
    icon_prefix = " " if is_redaccion else ""

    st.markdown(f"##{icon_prefix}Análisis de Crecimiento")

    # Selector de tipo de comparación
    col1, col2 = st.columns([1, 3])

    with col1:
        comparison_type = st.selectbox(
            "Tipo de comparación:",
            ["day", "week", "month", "90days", "custom"],
            format_func=lambda x: {
                "day": "Día vs Día anterior" if is_redaccion else "Día actual vs día anterior",
                "week": "Semana vs Semana anterior" if is_redaccion else "Semana actual vs semana anterior",
                "month": "Mes vs Mes anterior" if is_redaccion else "Mes actual vs mes anterior",
                "90days": "90 días vs 90 días anteriores" if is_redaccion else "90 días actuales vs 90 días anteriores",
                "custom": "Período personalizado"
            }[x],
            key=f"comparison_type_{config['page_type']}_{config['medio']}"
        )

    # Obtener URLs normalizadas del Sheet para filtrar
    sheets_urls_growth = None
    if not merged_df.empty and 'url_normalized' in merged_df.columns:
        sheets_urls_growth = merged_df['url_normalized'].dropna().unique().tolist()

    # Si es personalizado, mostrar selectores de fecha
    if comparison_type == "custom":
        st.markdown("**Período Actual:**")
        col1, col2 = st.columns(2)
        with col1:
            current_start = st.date_input(
                "Inicio actual:",
                value=datetime.now() - timedelta(days=7),
                key=f"growth_current_start_{config['page_type']}_{config['medio']}"
            )
        with col2:
            current_end = st.date_input(
                "Fin actual:",
                value=datetime.now(),
                key=f"growth_current_end_{config['page_type']}_{config['medio']}"
            )

        st.markdown("**Período de Comparación:**")
        col3, col4 = st.columns(2)
        with col3:
            previous_start = st.date_input(
                "Inicio comparación:",
                value=datetime.now() - timedelta(days=14),
                key=f"growth_previous_start_{config['page_type']}_{config['medio']}"
            )
        with col4:
            previous_end = st.date_input(
                "Fin comparación:",
                value=datetime.now() - timedelta(days=8),
                key=f"growth_previous_end_{config['page_type']}_{config['medio']}"
            )

        # Obtener datos personalizados
        growth_data = get_ga4_growth_data_custom(
            config['property_id'],
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
            config['property_id'],
            credentials_file,
            comparison_type,
            sheets_urls_growth
        )

    if growth_data:
        if is_redaccion:
            st.success(f"{icon_prefix}Comparando: {growth_data['period_name']}")

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
            delta_color = "normal" if growth_pct >= 0 or growth_pct == float('inf') else "inverse" if is_redaccion else "normal"
            st.metric(
                f"{icon_prefix}Page Views",
                f"{pv_data['current']:,}",
                delta=format_growth_percentage(growth_pct, pv_data['growth_absolute']),
                delta_color=delta_color
            )

        with col2:
            sessions_data = growth_data['data']['sessions']
            growth_pct = sessions_data['growth_percentage']
            delta_color = "normal" if growth_pct >= 0 or growth_pct == float('inf') else "inverse" if is_redaccion else "normal"
            st.metric(
                f"{icon_prefix}Sesiones",
                f"{sessions_data['current']:,}",
                delta=format_growth_percentage(growth_pct, sessions_data['growth_absolute']),
                delta_color=delta_color
            )

        with col3:
            users_data = growth_data['data']['users']
            growth_pct = users_data['growth_percentage']
            delta_color = "normal" if growth_pct >= 0 or growth_pct == float('inf') else "inverse" if is_redaccion else "normal"
            st.metric(
                f"{icon_prefix}Usuarios",
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
            title=f'Comparación de Métricas: {growth_data["period_name"]}' if not is_redaccion else None,
            color_discrete_map={
                'Actual': config['color'],
                'Anterior': '#cccccc'
            }
        )
        st.plotly_chart(fig_comparison, use_container_width=True)
    else:
        st.error(f"{icon_prefix}No se pudieron obtener los datos de crecimiento")


def render_dashboard(config):
    """
    Renderizar dashboard completo según configuración.

    Args:
        config (dict): Configuración del dashboard con los siguientes campos:
            - medio (str): Identificador del medio ('clarin', 'ole', etc.)
            - page_type (str): Tipo de página ('redaccion' o 'cliente')
            - page_title (str): Título de la página
            - page_icon (str): Icono de la página (opcional)
            - property_id (str): ID de propiedad de GA4
            - credentials_file (str): Archivo de credenciales (opcional)
            - domain (str): Dominio del medio
            - monthly_goal (int): Objetivo mensual de pageviews (opcional, default 3000000)
            - color (str): Color del medio para gráficos
    """
    # Configurar página
    _apply_page_config(config)

    # Aplicar estilos
    _apply_styles()

    # Verificar autenticación
    _check_authentication(config)

    # Obtener configuración del medio desde utils
    media_config = create_media_config()[config['medio']]

    # Actualizar config con datos del medio si no están presentes
    if 'color' not in config:
        config['color'] = media_config.get('color', '#1f77b4')
    if 'property_id' not in config:
        config['property_id'] = media_config['property_id']
    if 'domain' not in config:
        config['domain'] = media_config['domain']

    # Título
    st.title(f"{media_config['name']}")
    st.markdown("---")

    # Sidebar con opciones
    start_date_param, end_date_param = _render_sidebar_config(config)

    # Cargar datos
    sheets_filtered, ga4_df, credentials_file = _load_data(config, start_date_param, end_date_param)

    # Verificar si hay datos
    if sheets_filtered.empty and (ga4_df is None or ga4_df.empty):
        icon_prefix = " " if config['page_type'] == 'redaccion' else ""
        st.error(f"{icon_prefix}No se encontraron datos para mostrar")
        st.info(f"""
        **Posibles causas:**
        - No hay URLs de {config['domain']} en el Google Sheet
        - Error al conectar con Google Analytics 4
        - Credenciales incorrectas o sin permisos para la propiedad {config['property_id']}
        """)
    else:
        # Métricas de datos cargados en sidebar
        st.sidebar.metric("URLs en Sheet", len(sheets_filtered) if not sheets_filtered.empty else 0)
        if ga4_df is not None:
            st.sidebar.metric("Páginas en GA4", ga4_df['pagePath'].nunique())
        else:
            st.sidebar.metric("Páginas en GA4", 0)

        # Mergear datos si ambos están disponibles
        if not sheets_filtered.empty and ga4_df is not None and not ga4_df.empty:
            merged_df = merge_sheets_with_ga4(sheets_filtered, ga4_df, config['domain'])

            # Calcular pageviews del mes actual
            current_month_start = datetime.now().replace(day=1).strftime('%Y-%m-%d')
            current_month_today = datetime.now().strftime('%Y-%m-%d')

            ga4_monthly_df = get_ga4_data(
                config['property_id'],
                credentials_file,
                start_date=current_month_start,
                end_date=current_month_today
            )

            total_monthly_pageviews = 0
            if ga4_monthly_df is not None and not ga4_monthly_df.empty and not sheets_filtered.empty:
                merged_monthly = merge_sheets_with_ga4(sheets_filtered, ga4_monthly_df, config['domain'])
                if not merged_monthly.empty and 'screenPageViews' in merged_monthly.columns:
                    total_monthly_pageviews = merged_monthly['screenPageViews'].sum()

            # ==================== SECCIÓN 1: GAUGE ====================
            _render_gauge_section(config, total_monthly_pageviews)
            st.markdown("---")

            # ==================== SECCIÓN 2: PROGRESIÓN ====================
            _render_progression_section(config, merged_df, credentials_file)

            # ==================== SECCIÓN 3: PERFORMANCE POR AUTOR (solo redacción) ====================
            _render_author_performance(config, merged_df)

            # ==================== SECCIÓN 4: TOP URLS ====================
            _render_top_urls(config, merged_df, start_date_param, end_date_param)

            # ==================== SECCIÓN 5: COMPARATIVA DOMINIO VS SHEET ====================
            _render_domain_comparison(config, sheets_filtered, ga4_df, merged_df, credentials_file)

            # ==================== SECCIÓN 6: CRECIMIENTO ====================
            _render_growth_analysis(config, merged_df, credentials_file)

        elif ga4_df is not None and not ga4_df.empty:
            # Solo datos de GA4
            icon_prefix = " " if config['page_type'] == 'redaccion' else ""
            st.warning(f"{icon_prefix}No se encontraron URLs de {media_config['name']} en el Google Sheet. Mostrando solo datos de GA4.")

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
            icon_prefix = " " if config['page_type'] == 'redaccion' else ""
            st.warning(f"{icon_prefix}No se pudieron obtener datos de GA4. Mostrando solo datos del Google Sheet.")
            st.dataframe(sheets_filtered, use_container_width=True)

    # Footer
    st.markdown("---")
    icon_prefix = " " if config['page_type'] == 'redaccion' else ""
    st.caption(f"{icon_prefix}Dashboard de {media_config['name']} | Property ID: {config['property_id']} | Dominio: {config['domain']}")
