#!/usr/bin/env python3
"""
Script para aplicar la refactorización a las páginas restantes de redacción
"""

import subprocess
import os

# Definir los medios restantes con sus nombres de display
medios = [
    ('elespanol', 'El Español'),
    ('mundodeportivo', 'Mundo Deportivo'),
    ('natgeo', 'National Geographic'),
    ('vidae', 'Vidae'),
    ('bumeran', 'Bumeran'),
    ('sancor', 'Sancor')
]

TEMPLATE_FILE = "pages/redaccion-okdiario-20566.py"
PAGES_DIR = "pages"

def refactor_page(medio_key, medio_name):
    """Refactoriza una página de redacción"""

    # Encontrar el archivo
    result = subprocess.run(
        f"ls {PAGES_DIR}/redaccion-{medio_key}-*.py 2>/dev/null | head -1",
        shell=True,
        capture_output=True,
        text=True
    )

    file_path = result.stdout.strip()
    if not file_path:
        print(f"❌ {medio_name}: No se encontró el archivo")
        return False

    print(f"🔧 Procesando: {medio_name} ({file_path})")

    # Encontrar las líneas de referencia
    with open(file_path, 'r') as f:
        lines = f.readlines()

    # Encontrar línea de "# Métricas principales"
    start_line = None
    for i, line in enumerate(lines, 1):
        if '# Métricas principales' in line:
            start_line = i
            break

    # Encontrar línea de elif
    elif_line = None
    for i, line in enumerate(lines, 1):
        if 'elif ga4_df is not None and not ga4_df.empty:' in line:
            elif_line = i
            break

    if not start_line or not elif_line:
        print(f"  ❌ No se encontraron las líneas de referencia (start: {start_line}, elif: {elif_line})")
        return False

    print(f"  📍 Línea inicio: {start_line}, Línea elif: {elif_line}")

    # Construir el nuevo archivo
    # 1. Todo antes de "# Métricas principales"
    new_lines = lines[:start_line-1]

    # 2. Agregar contenido del template (líneas 229-843)
    with open(TEMPLATE_FILE, 'r') as f:
        template_lines = f.readlines()

    # Reemplazar okdiario/OK Diario con el medio actual
    refactored_section = []
    for line in template_lines[228:843]:  # índices 228-842 (líneas 229-843)
        line = line.replace('okdiario', medio_key)
        line = line.replace('OK Diario', medio_name)
        line = line.replace('_okdiario', f'_{medio_key}')
        refactored_section.append(line)

    new_lines.extend(refactored_section)

    # 3. Agregar todo desde el elif en adelante
    new_lines.extend(lines[elif_line-1:])

    # Escribir el archivo
    with open(file_path, 'w') as f:
        f.writelines(new_lines)

    final_line_count = len(new_lines)
    print(f"  ✅ Completado: {final_line_count} líneas")
    return True

# Procesar cada medio
print("=" * 60)
print("REFACTORIZANDO PÁGINAS DE REDACCIÓN")
print("=" * 60)
print()

exitosos = 0
fallidos = 0

for medio_key, medio_name in medios:
    if refactor_page(medio_key, medio_name):
        exitosos += 1
    else:
        fallidos += 1
    print()

print("=" * 60)
print("📊 RESUMEN")
print("=" * 60)
print(f"Total:     {len(medios)}")
print(f"Exitosos:  {exitosos}")
print(f"Fallidos:  {fallidos}")
print("=" * 60)