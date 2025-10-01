#!/usr/bin/env python3
"""
Script para eliminar todos los emojis de las páginas de redacción
"""

import os
import re

def remove_emojis(filepath):
    """Elimina todos los emojis del archivo"""

    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    original_content = content

    # Patrón para detectar emojis Unicode
    # Rango amplio que cubre la mayoría de emojis
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
        "]+",
        flags=re.UNICODE
    )

    # Eliminar emojis seguidos de espacio
    content = emoji_pattern.sub('', content)

    # Limpiar espacios múltiples que puedan quedar
    content = re.sub(r'  +', ' ', content)

    # Limpiar líneas que solo tengan espacios después de eliminar emojis
    content = re.sub(r'^\s+$', '', content, flags=re.MULTILINE)

    # Solo escribir si hubo cambios
    if content != original_content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    return False

def main():
    """Función principal"""
    print("Removing all emojis from redaccion pages...")

    pages_dir = 'pages'
    redaccion_files = [f for f in os.listdir(pages_dir) if f.startswith('redaccion-') and f.endswith('.py')]

    fixed_count = 0
    for filename in redaccion_files:
        filepath = os.path.join(pages_dir, filename)
        print(f"\nProcessing {filename}...")

        if remove_emojis(filepath):
            print(f"Fixed {filename}")
            fixed_count += 1
        else:
            print(f"No changes needed for {filename}")

    print(f"\nFixed {fixed_count} of {len(redaccion_files)} redaccion pages!")

if __name__ == '__main__':
    main()
