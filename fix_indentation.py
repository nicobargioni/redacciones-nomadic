#!/usr/bin/env python3
"""
Script para arreglar la indentación incorrecta causada por la eliminación de emojis
"""

import os
import re

def fix_indentation(filepath):
    """Arregla la indentación del archivo"""

    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    original_content = ''.join(lines)
    fixed_lines = []

    for line in lines:
        # Detectar líneas que empiezan con espacio simple en lugar de 4 espacios
        # y están dentro de bloques de código
        if line.startswith(' ') and not line.startswith('    ') and not line.startswith('  '):
            # Contar cuántos espacios tiene
            leading_spaces = len(line) - len(line.lstrip(' '))
            if leading_spaces == 1:
                # Reemplazar espacio simple por 4 espacios
                line = '    ' + line.lstrip(' ')
        fixed_lines.append(line)

    fixed_content = ''.join(fixed_lines)

    # Solo escribir si hubo cambios
    if fixed_content != original_content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(fixed_content)
        return True
    return False

def main():
    """Función principal"""
    print("Fixing indentation in redaccion pages...")

    pages_dir = 'pages'
    redaccion_files = [f for f in os.listdir(pages_dir) if f.startswith('redaccion-') and f.endswith('.py')]

    fixed_count = 0
    for filename in redaccion_files:
        filepath = os.path.join(pages_dir, filename)
        print(f"\nProcessing {filename}...")

        if fix_indentation(filepath):
            print(f"Fixed {filename}")
            fixed_count += 1
        else:
            print(f"No changes needed for {filename}")

    print(f"\nFixed {fixed_count} of {len(redaccion_files)} redaccion pages!")

if __name__ == '__main__':
    main()
