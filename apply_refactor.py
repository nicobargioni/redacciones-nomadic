#!/usr/bin/env python3
"""
Script para eliminar contenido duplicado de tabs en todas las páginas de redacción
"""

import re
import glob

def remove_duplicate_content(filepath):
    """
    Elimina el contenido duplicado entre las dos ocurrencias de 'elif ga4_df is not None'
    """
    print(f"Procesando: {filepath}")

    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    # Encontrar todas las líneas que contienen 'elif ga4_df is not None and not ga4_df.empty:'
    elif_lines = []
    for i, line in enumerate(lines):
        if 'elif ga4_df is not None and not ga4_df.empty:' in line:
            elif_lines.append(i)

    if len(elif_lines) >= 2:
        print(f"  Encontradas {len(elif_lines)} ocurrencias de elif en líneas: {[l+1 for l in elif_lines]}")
        print(f"  Eliminando líneas {elif_lines[0]+1} a {elif_lines[1]}")

        # Mantener todo antes de la primera ocurrencia y desde la segunda en adelante
        new_lines = lines[:elif_lines[0]] + lines[elif_lines[1]:]

        with open(filepath, 'w', encoding='utf-8') as f:
            f.writelines(new_lines)

        print(f"  ✓ Archivo actualizado: {len(lines)} -> {len(new_lines)} líneas (eliminadas {len(lines) - len(new_lines)} líneas)")
        return True
    else:
        print(f"  No se encontró contenido duplicado (solo {len(elif_lines)} ocurrencia(s) de elif)")
        return False

# Procesar todas las páginas de redacción
redaccion_pages = glob.glob('/Users/nico/Documents/vscode/redacciones-nomadic/pages/redaccion-*.py')

print(f"Encontradas {len(redaccion_pages)} páginas de redacción\n")

processed = 0
skipped = 0

for page in sorted(redaccion_pages):
    if remove_duplicate_content(page):
        processed += 1
    else:
        skipped += 1
    print()

print(f"\n=== RESUMEN ===")
print(f"Procesadas: {processed}")
print(f"Omitidas: {skipped}")
print(f"Total: {len(redaccion_pages)}")