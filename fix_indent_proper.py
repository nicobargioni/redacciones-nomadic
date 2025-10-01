#!/usr/bin/env python3
"""
Script para arreglar correctamente la indentación
El problema: después de eliminar emojis, se perdió la indentación correcta
"""

import os
import subprocess

def fix_file_with_autopep8(filepath):
    """Usa autopep8 para arreglar indentación"""
    try:
        result = subprocess.run(
            ['python3', '-m', 'autopep8', '--in-place', '--select=E101,E111,E112,E113,E114,E115,E116,E117', filepath],
            capture_output=True,
            text=True
        )
        return result.returncode == 0
    except Exception as e:
        print(f"Error: {e}")
        return False

def manual_indent_fix(filepath):
    """Arreglo manual de indentación específico"""
    with open(filepath, 'r') as f:
        lines = f.readlines()

    fixed_lines = []
    indent_stack = [0]  # Pila de niveles de indentación

    for i, line in enumerate(lines):
        stripped = line.lstrip()

        if not stripped or stripped.startswith('#'):
            # Líneas vacías o comentarios, mantener
            fixed_lines.append(line)
            continue

        # Detectar apertura de bloques
        if stripped.rstrip().endswith(':'):
            # Esta línea abre un bloque
            current_indent = indent_stack[-1]
            fixed_line = ' ' * current_indent + stripped
            fixed_lines.append(fixed_line)
            indent_stack.append(current_indent + 4)
        # Detectar cierre de bloques
        elif line.lstrip().startswith(('else:', 'elif ', 'except:', 'except ', 'finally:', 'with ')):
            # Cerrar bloque anterior si es else/elif/etc
            if len(indent_stack) > 1 and not line.lstrip().startswith('with '):
                indent_stack.pop()
            current_indent = indent_stack[-1]
            fixed_line = ' ' * current_indent + stripped
            fixed_lines.append(fixed_line)
            if stripped.rstrip().endswith(':'):
                indent_stack.append(current_indent + 4)
        else:
            # Línea normal, usar indentación actual
            current_indent = indent_stack[-1]

            # Detectar fin de expresión (cierre de paréntesis/corchetes)
            if stripped.startswith((']', ')', '}')) and not stripped.rstrip().endswith(':'):
                # Puede ser que necesite des-indentar
                if len(indent_stack) > 1:
                    indent_stack.pop()
                    current_indent = indent_stack[-1]

            fixed_line = ' ' * current_indent + stripped
            fixed_lines.append(fixed_line)

    with open(filepath, 'w') as f:
        f.writelines(fixed_lines)

    return True

def main():
    """Función principal"""
    print("Fixing indentation properly...")

    # Primero intentar instalar autopep8
    print("Installing autopep8...")
    subprocess.run(['python3', '-m', 'pip', 'install', 'autopep8', '-q'], capture_output=True)

    pages_dir = 'pages'
    redaccion_files = [f for f in os.listdir(pages_dir) if f.startswith('redaccion-') and f.endswith('.py')]

    for filename in redaccion_files:
        filepath = os.path.join(pages_dir, filename)
        print(f"\nProcessing {filename}...")

        # Intentar con autopep8
        if fix_file_with_autopep8(filepath):
            # Verificar sintaxis
            result = subprocess.run(['python3', '-m', 'py_compile', filepath], capture_output=True)
            if result.returncode == 0:
                print(f"  Fixed {filename}")
            else:
                print(f"  autopep8 failed, trying manual fix...")
                manual_indent_fix(filepath)
                result = subprocess.run(['python3', '-m', 'py_compile', filepath], capture_output=True)
                if result.returncode == 0:
                    print(f"  Manually fixed {filename}")
                else:
                    print(f"  ERROR: Could not fix {filename}")
                    print(result.stderr.decode())
        else:
            print(f"  autopep8 not available, trying manual fix...")
            manual_indent_fix(filepath)

    print("\nDone!")

if __name__ == '__main__':
    main()
