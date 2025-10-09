#!/usr/bin/env python3
"""
Script para agregar selectores de tiempo en la sección Comparativa
de todas las páginas de cliente y redacción.
"""

import os
import re

# Directorio con las páginas
pages_dir = "pages"

# Mapeo de nombres de archivos a sus claves únicas
file_keys = {
    "ole-412346632.py": "ole",
    "okdiario-431468943.py": "okdiario",
    "elespanol-421272699.py": "elespanol",
    "mundodeportivo-491737805.py": "mundodeportivo",
    "natgeo-770032477.py": "natgeo",
    "vidae-599772643.py": "vidae",
    "bumeran-251450665.py": "bumeran",
    "sancor-537029540.py": "sancor",
    "redaccion-clarin-85046.py": "redaccion_clarin",
    "redaccion-ole-40453.py": "redaccion_ole",
    "redaccion-okdiario-20566.py": "redaccion_okdiario",
    "redaccion-elespanol-73498.py": "redaccion_elespanol",
    "redaccion-mundodeportivo-84048.py": "redaccion_mundodeportivo",
    "redaccion-natgeo-78696.py": "redaccion_natgeo",
    "redaccion-vidae-15766.py": "redaccion_vidae",
    "redaccion-bumeran-77169.py": "redaccion_bumeran",
    "redaccion-sancor-67127.py": "redaccion_sancor"
}

def update_file(filepath, key):
    """Actualizar un archivo con los nuevos selectores"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Patrón a buscar (sección comparativa actual)
    old_pattern = r'(# ={20} SECCIÓN 4: COMPARATIVA DOMINIO VS SHEET ={20}\s+st\.markdown\("## Comparativa: Dominio Completo vs URLs del Sheet"\)\s+st\.caption\(f"Período de análisis: \{start_date_param\} a \{end_date_param\}"\)\s+# Obtener datos del dominio completo \(sin home\) usando el período seleccionado\s+# Convertir el período al formato adecuado si es necesario\s+if start_date_param\.endswith\("daysAgo"\):\s+days = int\(start_date_param\.replace\("daysAgo", ""\)\)\s+period_start = \(datetime\.now\(\) - timedelta\(days=days\)\)\.strftime\(\'%Y-%m-%d\'\)\s+else:\s+period_start = start_date_param\s+if end_date_param == "today":\s+period_end = datetime\.now\(\)\.strftime\(\'%Y-%m-%d\'\)\s+else:\s+period_end = end_date_param\s+# Usar los datos de GA4 ya cargados para la comparativa\s+if ga4_df is not None and not ga4_df\.empty:)'

    # Nuevo contenido
    new_content = f'''        # ==================== SECCIÓN 4: COMPARATIVA DOMINIO VS SHEET ====================
        st.markdown("## Comparativa: Dominio Completo vs URLs del Sheet")

        # Selectores de tiempo para la comparativa
        col1, col2 = st.columns([1, 3])

        with col1:
            comparison_date_option = st.selectbox(
                "Rango de fechas:",
                ["7daysAgo", "14daysAgo", "30daysAgo", "90daysAgo", "Personalizado"],
                format_func=lambda x: {{
                    "7daysAgo": "Últimos 7 días",
                    "14daysAgo": "Últimos 14 días",
                    "30daysAgo": "Últimos 30 días",
                    "90daysAgo": "Últimos 90 días",
                    "Personalizado": "Personalizado"
                }}[x],
                key="comparison_date_range_{key}"
            )

        # Si es personalizado, mostrar selectores de fecha
        if comparison_date_option == "Personalizado":
            col1, col2 = st.columns(2)
            with col1:
                comparison_start_date = st.date_input(
                    "Fecha inicio:",
                    value=datetime.now() - timedelta(days=7),
                    key="comparison_start_{key}"
                )
            with col2:
                comparison_end_date = st.date_input(
                    "Fecha fin:",
                    value=datetime.now(),
                    key="comparison_end_{key}"
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

        st.caption(f"Período de análisis: {{period_start}} a {{period_end}}")

        # Cargar datos de GA4 para la comparativa con el rango seleccionado
        with st.spinner('Cargando datos de comparativa...'):
            ga4_comparison_df = get_ga4_data(
                media_config['property_id'],
                credentials_file,
                start_date=comparison_start_param,
                end_date=comparison_end_param
            )

        # Usar los datos de GA4 de la comparativa
        if ga4_comparison_df is not None and not ga4_comparison_df.empty:'''

    # Buscar y reemplazar usando búsqueda de texto simple
    search_str = '''        # ==================== SECCIÓN 4: COMPARATIVA DOMINIO VS SHEET ====================
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
        if ga4_df is not None and not ga4_df.empty:'''

    if search_str in content:
        content = content.replace(search_str, new_content)

        # También actualizar las referencias de ga4_df a ga4_comparison_df
        search_str2 = '''            # Calcular métricas del dominio completo desde ga4_df
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
            sheet_pages = len(merged_df)'''

        new_content2 = '''            # Mergear datos del Sheet con GA4 del período seleccionado
            merged_comparison_df = merge_sheets_with_ga4(sheets_filtered, ga4_comparison_df, media_config['domain'])

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
            sheet_pages = len(merged_comparison_df)'''

        if search_str2 in content:
            content = content.replace(search_str2, new_content2)

            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)

            return True

    return False

def main():
    """Función principal"""
    # Saltar clarin porque ya fue editado
    files_to_update = [f for f in file_keys.keys() if f != "clarin-106275640.py"]

    updated = 0
    failed = 0

    for filename in files_to_update:
        filepath = os.path.join(pages_dir, filename)
        if os.path.exists(filepath):
            key = file_keys[filename]
            if update_file(filepath, key):
                print(f"✓ Actualizado: {filename}")
                updated += 1
            else:
                print(f"✗ No se pudo actualizar: {filename}")
                failed += 1
        else:
            print(f"⚠ No encontrado: {filename}")
            failed += 1

    print(f"\nResumen: {updated} actualizados, {failed} fallidos")

if __name__ == "__main__":
    main()
