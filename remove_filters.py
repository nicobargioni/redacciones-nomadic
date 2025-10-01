#!/usr/bin/env python3
"""
Script para eliminar los filtros de fuente y medio de todas las páginas de redacción
"""

import os
import re

def remove_source_medium_filters(filepath):
    """Elimina los filtros de fuente y medio de GA4"""

    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    original_content = content

    # Patrón para encontrar y eliminar toda la sección de filtros
    # Desde "# Agregar filtros por fuente y medio de GA4" hasta antes de "# Métricas de datos cargados"
    pattern = r"    # Agregar filtros por fuente y medio de GA4\n.*?(?=    # Métricas de datos cargados)"

    content = re.sub(pattern, '', content, flags=re.DOTALL)

    # Ahora simplificar la lógica de merge
    # Buscar la sección que tiene toda la lógica de filtrado GA4
    merge_pattern = r"    # Mergear datos si ambos están disponibles\n    if not sheets_filtered\.empty and ga4_df is not None and not ga4_df\.empty:\n        # Aplicar filtros de fuente y medio a GA4 antes del merge\n        ga4_filtered = ga4_df\.copy\(\)\n        \n        # Agregar columna url_normalized a ga4_filtered ANTES de aplicar filtros\n        ga4_filtered\['url_normalized'\] = ga4_filtered\['pagePath'\]\.apply\(\n            lambda x: normalize_url\(f\"\{media_config\['domain'\]\}\{x\}\"\)\n        \)\n        \n        if source_filter:\n            ga4_filtered = ga4_filtered\[ga4_filtered\['sessionSource'\]\.isin\(source_filter\)\]\n        \n        if medium_filter:\n            ga4_filtered = ga4_filtered\[ga4_filtered\['sessionMedium'\]\.isin\(medium_filter\)\]\n        \n        if not ga4_filtered\.empty:\n            merged_df = merge_sheets_with_ga4\(sheets_filtered, ga4_filtered, media_config\['domain'\]\)\n            \n            # Mostrar información de filtros aplicados\n            if source_filter or medium_filter:\n                filter_info = \[\]\n                if source_filter:\n                    filter_info\.append\(f\"Fuentes: \{len\(source_filter\)\}\"\)\n                if medium_filter:\n                    filter_info\.append\(f\"Medios: \{len\(medium_filter\)\}\"\)\n                st\.sidebar\.success\(f\"🎯 Filtros GA4: \{', '\.join\(filter_info\)\}\"\)\n        else:\n            st\.warning\(\"⚠️ Los filtros de fuente/medio no devolvieron datos de GA4\"\)\n            merged_df = sheets_filtered  # Solo datos del sheet"

    merge_replacement = """    # Mergear datos si ambos están disponibles
    if not sheets_filtered.empty and ga4_df is not None and not ga4_df.empty:
        merged_df = merge_sheets_with_ga4(sheets_filtered, ga4_df, media_config['domain'])"""

    content = re.sub(merge_pattern, merge_replacement, content)

    # Solo escribir si hubo cambios
    if content != original_content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    return False

def main():
    """Función principal"""
    print("🗑️  Removing source and medium filters from all redaccion pages...")

    pages_dir = 'pages'
    redaccion_files = [f for f in os.listdir(pages_dir) if f.startswith('redaccion-') and f.endswith('.py')]

    fixed_count = 0
    for filename in redaccion_files:
        filepath = os.path.join(pages_dir, filename)
        print(f"\n📝 Processing {filename}...")

        if remove_source_medium_filters(filepath):
            print(f"✓ Fixed {filename}")
            fixed_count += 1
        else:
            print(f"○ No changes needed for {filename}")

    print(f"\n✅ Fixed {fixed_count} of {len(redaccion_files)} redaccion pages!")

    if fixed_count > 0:
        print("\n🗑️  Filters removed:")
        print("  - 🌐 Filtrar por Fuente (sessionSource)")
        print("  - 📡 Filtrar por Medio (sessionMedium)")

if __name__ == '__main__':
    main()
