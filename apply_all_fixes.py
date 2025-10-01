#!/usr/bin/env python3
"""
Script para aplicar todas las correcciones a las páginas de redacción:
1. Gauge sin colores internos y límite exacto
2. Eliminar filtros de fuente y medio
3. Eliminar emojis (solo los caracteres, preservando espacios e indentación)
"""

import os
import re

def apply_all_fixes(filepath):
    """Aplica todas las correcciones a una página de redacción"""

    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    original_content = content

    # 1. Fix gauge configuration
    gauge_pattern = r"            gauge = \{\n                'axis': \{'range': \[None, monthly_goal \* 1\.2\]\},\n                'bar': \{'color': media_config\['color'\]\},\n                'steps': \[\n                    \{'range': \[0, monthly_goal \* 0\.5\], 'color': \"lightgray\"\},\n                    \{'range': \[monthly_goal \* 0\.5, monthly_goal \* 0\.8\], 'color': \"yellow\"\},\n                    \{'range': \[monthly_goal \* 0\.8, monthly_goal\], 'color': \"lightgreen\"\}\n                \],\n                'threshold': \{\n                    'line': \{'color': \"#4A107A\", 'width': 4\},\n                    'thickness': 0\.75,\n                    'value': monthly_goal\n                \}\n            \}"

    gauge_replacement = """            gauge = {
                'axis': {'range': [None, monthly_goal]},
                'bar': {'color': media_config['color']},
                'threshold': {
                    'line': {'color': "#4A107A", 'width': 4},
                    'thickness': 0.75,
                    'value': monthly_goal
                }
            }"""

    content = re.sub(gauge_pattern, gauge_replacement, content)

    # 2. Remove source/medium filters section
    filter_pattern = r"    # Agregar filtros por fuente y medio de GA4\n.*?(?=    # Métricas de datos cargados)"
    content = re.sub(filter_pattern, '', content, flags=re.DOTALL)

    # 3. Simplify merge logic
    merge_pattern = r"    # Mergear datos si ambos están disponibles\n    if not sheets_filtered\.empty and ga4_df is not None and not ga4_df\.empty:\n        # Aplicar filtros de fuente y medio a GA4 antes del merge\n        ga4_filtered = ga4_df\.copy\(\)\n        \n        # Agregar columna url_normalized a ga4_filtered ANTES de aplicar filtros\n        ga4_filtered\['url_normalized'\] = ga4_filtered\['pagePath'\]\.apply\(\n            lambda x: normalize_url\(f\"\{media_config\['domain'\]\}\{x\}\"\)\n        \)\n        \n        if source_filter:\n            ga4_filtered = ga4_filtered\[ga4_filtered\['sessionSource'\]\.isin\(source_filter\)\]\n        \n        if medium_filter:\n            ga4_filtered = ga4_filtered\[ga4_filtered\['sessionMedium'\]\.isin\(medium_filter\)\]\n        \n        if not ga4_filtered\.empty:\n            merged_df = merge_sheets_with_ga4\(sheets_filtered, ga4_filtered, media_config\['domain'\]\)\n            \n            # Mostrar información de filtros aplicados\n            if source_filter or medium_filter:\n                filter_info = \[\]\n                if source_filter:\n                    filter_info\.append\(f\"Fuentes: \{len\(source_filter\)\}\"\)\n                if medium_filter:\n                    filter_info\.append\(f\"Medios: \{len\(medium_filter\)\}\"\)\n                st\.sidebar\.success\(f\"🎯 Filtros GA4: \{', '\.join\(filter_info\)\}\"\)\n        else:\n            st\.warning\(\"⚠️ Los filtros de fuente/medio no devolvieron datos de GA4\"\)\n            merged_df = sheets_filtered  # Solo datos del sheet"

    merge_replacement = """    # Mergear datos si ambos están disponibles
    if not sheets_filtered.empty and ga4_df is not None and not ga4_df.empty:
        merged_df = merge_sheets_with_ga4(sheets_filtered, ga4_df, media_config['domain'])"""

    content = re.sub(merge_pattern, merge_replacement, content)

    # 4. Remove emojis (preserving all whitespace and structure)
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"  # emoticons
        "\U0001F300-\U0001F5FF"  # symbols & pictographs
        "\U0001F680-\U0001F6FF"  # transport & map symbols
        "\U0001F1E0-\U0001F1FF"  # flags (iOS)
        "\U00002702-\U000027B0"
        "\U000024C2-\U0001F251"
        "\U0001F900-\U0001F9FF"  # Supplemental Symbols and Pictographs
        "\U0001FA00-\U0001FA6F"  # Chess Symbols
        "\U0001FA70-\U0001FAFF"  # Symbols and Pictographs Extended-A
        "\u2600-\u26FF"          # Miscellaneous Symbols
        "\u2700-\u27BF"          # Dingbats
        "]",
        flags=re.UNICODE
    )

    # Remove emojis but keep all whitespace intact
    content = emoji_pattern.sub('', content)

    # Solo escribir si hubo cambios
    if content != original_content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    return False

def main():
    """Función principal"""
    print("Applying all fixes to redaccion pages...")

    pages_dir = 'pages'
    redaccion_files = [f for f in os.listdir(pages_dir) if f.startswith('redaccion-') and f.endswith('.py')]

    fixed_count = 0
    for filename in redaccion_files:
        filepath = os.path.join(pages_dir, filename)
        print(f"\nProcessing {filename}...")

        if apply_all_fixes(filepath):
            print(f"Fixed {filename}")
            fixed_count += 1
        else:
            print(f"No changes needed for {filename}")

    print(f"\nFixed {fixed_count} of {len(redaccion_files)} redaccion pages!")

    print("\nChanges applied:")
    print("  - Gauge: removed internal colors, set limit to exact goal")
    print("  - Removed source/medium filters")
    print("  - Removed all emojis")

if __name__ == '__main__':
    main()
