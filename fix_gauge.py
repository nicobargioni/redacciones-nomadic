#!/usr/bin/env python3
"""
Script para:
1. Eliminar los colores internos del gauge (steps)
2. Cambiar el límite del gauge a monthly_goal exacto (no monthly_goal * 1.2)
"""

import os
import re

def fix_gauge_config(filepath):
    """Elimina steps del gauge y ajusta el límite al objetivo exacto"""

    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    original_content = content

    # Buscar y reemplazar la configuración del gauge
    # Patrón que captura todo el bloque gauge con steps
    pattern = r"            gauge = \{\n                'axis': \{'range': \[None, monthly_goal \* 1\.2\]\},\n                'bar': \{'color': media_config\['color'\]\},\n                'steps': \[\n                    \{'range': \[0, monthly_goal \* 0\.5\], 'color': \"lightgray\"\},\n                    \{'range': \[monthly_goal \* 0\.5, monthly_goal \* 0\.8\], 'color': \"yellow\"\},\n                    \{'range': \[monthly_goal \* 0\.8, monthly_goal\], 'color': \"lightgreen\"\}\n                \],\n                'threshold': \{\n                    'line': \{'color': \"#4A107A\", 'width': 4\},\n                    'thickness': 0\.75,\n                    'value': monthly_goal\n                \}\n            \}"

    replacement = """            gauge = {
                'axis': {'range': [None, monthly_goal]},
                'bar': {'color': media_config['color']},
                'threshold': {
                    'line': {'color': "#4A107A", 'width': 4},
                    'thickness': 0.75,
                    'value': monthly_goal
                }
            }"""

    content = re.sub(pattern, replacement, content)

    # Solo escribir si hubo cambios
    if content != original_content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    return False

def main():
    """Función principal"""
    print("🎨 Fixing gauge configuration in all redaccion pages...")

    pages_dir = 'pages'
    redaccion_files = [f for f in os.listdir(pages_dir) if f.startswith('redaccion-') and f.endswith('.py')]

    fixed_count = 0
    for filename in redaccion_files:
        filepath = os.path.join(pages_dir, filename)
        print(f"\n📝 Processing {filename}...")

        if fix_gauge_config(filepath):
            print(f"✓ Fixed {filename}")
            fixed_count += 1
        else:
            print(f"○ No changes needed for {filename}")

    print(f"\n✅ Fixed {fixed_count} of {len(redaccion_files)} redaccion pages!")

    if fixed_count > 0:
        print("\n🎨 Gauge changes applied:")
        print("  - Removed internal color steps (lightgray, yellow, lightgreen)")
        print("  - Changed axis limit from monthly_goal * 1.2 to monthly_goal")

if __name__ == '__main__':
    main()
