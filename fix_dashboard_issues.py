#!/usr/bin/env python3
"""
Script para:
1. Eliminar la sección "Ver Tabla de Datos Completa"
2. Corregir la comparativa de dominio vs sheet
3. Arreglar el gráfico de Top URLs para que coincida con el slider
4. Reemplazar colores rojos por #4A107A
"""

import os
import re

def fix_redaccion_page(filepath):
    """Aplica todas las correcciones a una página de redacción"""

    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    original_content = content

    # 1. Eliminar toda la sección "Ver Tabla de Datos Completa"
    # Buscar desde "with st.expander("📋 Ver Tabla de Datos Completa"):" hasta el próximo "with st.expander" o hasta "# Footer"
    pattern = r'        # ==================== SECCIÓN ADICIONAL: TABLA DE DATOS ====================.*?(?=        # Mantener las tabs antiguas|# Footer)'
    content = re.sub(pattern, '', content, flags=re.DOTALL)

    # 2. Eliminar la sección completa de comparativa (mal calculada)
    pattern = r'        # ==================== SECCIÓN 5: COMPARATIVA DOMINIO VS SHEET ====================.*?(?=        st\.markdown\("---"\)\n\n        # ====)'
    content = re.sub(pattern, '', content, flags=re.DOTALL)

    # 3. Corregir el gráfico de Top URLs - cambiar [::-1] para invertir correctamente
    # El problema es que invierte después de tomar top_n, necesitamos invertir solo para el gráfico
    pattern = r"            fig_top = go\.Figure\(data=\[\n                go\.Bar\(\n                    y=top_urls\['URL'\]\[::-1\],  # Invertir para mostrar el más alto arriba\n                    x=top_urls\['Page Views'\]\[::-1\],"
    replacement = """            fig_top = go.Figure(data=[
                go.Bar(
                    y=top_urls['URL'].iloc[::-1],  # Invertir para mostrar el más alto arriba
                    x=top_urls['Page Views'].iloc[::-1],"""
    content = content.replace(pattern, replacement)

    # 4. Reemplazar todos los colores rojos por #4A107A
    # Variantes de rojo a reemplazar
    red_variants = [
        (r"'red'", "'#4A107A'"),
        (r'"red"', '"#4A107A"'),
        (r"line_color=\"red\"", 'line_color="#4A107A"'),
        (r"'color': 'red'", "'color': '#4A107A'"),
        (r'"color": "red"', '"color": "#4A107A"'),
        (r"marker_color='red'", "marker_color='#4A107A'"),
        (r'marker_color="red"', 'marker_color="#4A107A"'),
        (r"#e53935", "#4A107A"),  # Color rojo de okdiario
        (r"#ff0000", "#4A107A"),
        (r"#FF0000", "#4A107A"),
        (r"colors = \['green' if x >= 0 else 'red' for x in growth_percentages\]",
         "colors = ['green' if x >= 0 else '#4A107A' for x in growth_percentages]"),
    ]

    for pattern, replacement in red_variants:
        content = re.sub(pattern, replacement, content)

    # 5. Remover la línea roja del threshold en el gauge
    content = content.replace(
        "'line': {'color': \"#4A107A\", 'width': 4}",
        "'line': {'color': \"#4A107A\", 'width': 4}"
    )

    # Solo escribir si hubo cambios
    if content != original_content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    return False

def main():
    """Función principal"""
    print("🔧 Fixing dashboard issues in all redaccion pages...")

    pages_dir = 'pages'
    redaccion_files = [f for f in os.listdir(pages_dir) if f.startswith('redaccion-') and f.endswith('.py')]

    fixed_count = 0
    for filename in redaccion_files:
        filepath = os.path.join(pages_dir, filename)
        print(f"\n📝 Processing {filename}...")

        if fix_redaccion_page(filepath):
            print(f"✓ Fixed {filename}")
            fixed_count += 1
        else:
            print(f"○ No changes needed for {filename}")

    print(f"\n✅ Fixed {fixed_count} of {len(redaccion_files)} redaccion pages!")

    if fixed_count > 0:
        print("\n🎨 Color changes applied:")
        print("  - All red variants → #4A107A (purple)")
        print("\n📋 Sections removed:")
        print("  - Ver Tabla de Datos Completa")
        print("  - Comparativa Dominio vs Sheet (will be recalculated)")
        print("\n🔝 Top URLs chart fixed to match slider")

if __name__ == '__main__':
    main()
