#!/usr/bin/env python3
"""
Script para refactorizar las páginas de Streamlit eliminando tabs
y reorganizando el contenido en secciones lineales
"""

import re
import glob

# Template para la nueva estructura (después de merged_df)
TEMPLATE_NUEVA_ESTRUCTURA = '''
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
        st.markdown("## 📊 KPI Mensual")

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

        st.markdown("---")

        # ==================== SECCIÓN 2: PROGRESIÓN DEL OBJETIVO ====================
        st.markdown("## 📈 Progresión del Objetivo a lo largo del Mes")

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
                line=dict(color='red', width=2, dash='dash')
            ))

            fig_progression.update_layout(
                title='Progresión Acumulada de Page Views del Mes',
                xaxis_title='Fecha',
                yaxis_title='Page Views Acumulados',
                hovermode='x unified',
                height=400
            )

            st.plotly_chart(fig_progression, use_container_width=True)
        else:
            st.warning("No se pudieron cargar los datos de progresión del mes")

        st.markdown("---")

        # ==================== SECCIÓN 3: PERFORMANCE POR AUTOR ====================
        st.markdown("## 👤 Performance por Autor")

        if not sheets_filtered.empty and 'autor' in merged_df.columns and 'screenPageViews' in merged_df.columns:
            # Agrupar por autor y sumar pageviews
            author_performance = merged_df.groupby('autor').agg({
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
                    marker_color=media_config['color'],
                    text=author_performance['Total Page Views'].apply(lambda x: f'{x:,.0f}'),
                    textposition='outside'
                )
            ])

            fig_authors.update_layout(
                title='Total Page Views por Autor',
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
        else:
            st.info("No hay datos de autores disponibles")

        st.markdown("---")

        # ==================== SECCIÓN 4: TOP URLS ====================
        st.markdown("## 🔝 Top URLs según Page Views")

        top_n = st.slider("Número de URLs a mostrar:", 5, 50, 20, key="top_urls_slider")

        if 'screenPageViews' in merged_df.columns:
            # Seleccionar columnas relevantes para mostrar
            display_columns = []
            if 'titulo' in merged_df.columns:
                display_columns.append('titulo')
            display_columns.extend(['url_normalized', 'screenPageViews'])
            if 'autor' in merged_df.columns:
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

        # ==================== SECCIÓN 5: COMPARATIVA DOMINIO VS SHEET ====================
        st.markdown("## 🔄 Comparativa: Dominio Completo vs URLs del Sheet")

        # Obtener datos del dominio completo (sin home)
        pageviews_data = get_ga4_pageviews_data(
            media_config['property_id'],
            credentials_file,
            period="month"
        )

        if pageviews_data and 'screenPageViews' in merged_df.columns:
            # Métricas comparativas
            domain_total_pv = pageviews_data['total_pageviews']
            domain_no_home_pv = pageviews_data['non_home_pageviews']
            domain_pages = pageviews_data['non_home_pages']

            sheet_total_pv = merged_df['screenPageViews'].sum()
            sheet_pages = len(merged_df)

            col1, col2 = st.columns(2)

            with col1:
                st.markdown("### 🌐 Dominio Completo (sin home)")
                st.metric("Total Page Views", f"{domain_no_home_pv:,.0f}")
                st.metric("Páginas Únicas", f"{domain_pages:,.0f}")
                avg_domain = domain_no_home_pv / domain_pages if domain_pages > 0 else 0
                st.metric("Promedio PV/Página", f"{avg_domain:,.0f}")

            with col2:
                st.markdown("### 📰 URLs del Sheet")
                st.metric("Total Page Views", f"{sheet_total_pv:,.0f}")
                st.metric("Páginas Únicas", f"{sheet_pages:,.0f}")
                avg_sheet = sheet_total_pv / sheet_pages if sheet_pages > 0 else 0
                st.metric("Promedio PV/Página", f"{avg_sheet:,.0f}")

            # Calcular porcentaje de representación
            if domain_no_home_pv > 0:
                representation_pct = (sheet_total_pv / domain_no_home_pv) * 100
                st.info(f"📊 Las URLs del Sheet representan el **{representation_pct:.1f}%** del tráfico total del dominio (sin home)")

            # Gráfico comparativo
            comparison_data = pd.DataFrame({
                'Categoría': ['Dominio Completo\\n(sin home)', 'URLs del Sheet'],
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
                        'Dominio Completo\\n(sin home)': '#808080',
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
                        'Dominio Completo\\n(sin home)': '#808080',
                        'URLs del Sheet': media_config['color']
                    }
                )
                fig_avg.update_layout(showlegend=False)
                st.plotly_chart(fig_avg, use_container_width=True)
        else:
            st.error("No se pudieron obtener los datos comparativos")

        st.markdown("---")

        # ==================== SECCIÓN ADICIONAL: TABLA DE DATOS ====================
        with st.expander("📋 Ver Tabla de Datos Completa"):
            st.markdown("### Datos Combinados (Sheet + GA4)")

            # Búsqueda
            search = st.text_input("🔍 Buscar:", "", key="search_table_data")
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
                file_name=f"data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                key="download_csv_data"
            )
'''

print("Script creado pero no se ejecutará automáticamente")
print("Por favor revisa el template antes de aplicarlo")