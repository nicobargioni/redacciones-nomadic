#!/usr/bin/env python3
"""
Script para replicar la estructura de redaccion-okdiario-20566.py a todas las demás páginas de redacción
"""

import os
import re

# Definir el mapeo de medios con sus configuraciones
MEDIOS = {
    'clarin': {
        'name': 'Clarín',
        'icon': '📰',
        'key_suffix': 'clarin',
        'domain': 'clarin.com',
        'credentials': 'credentials_analytics_acceso_medios.json',
        'monthly_goal': 3000000
    },
    'ole': {
        'name': 'Olé',
        'icon': '⚽',
        'key_suffix': 'ole',
        'domain': 'ole.com.ar',
        'credentials': 'credentials_analytics_acceso_medios.json',
        'monthly_goal': 3000000
    },
    'elespanol': {
        'name': 'El Español',
        'icon': '🇪🇸',
        'key_suffix': 'elespanol',
        'domain': 'elespanol.com',
        'credentials': 'credentials_analytics_acceso_medios.json',
        'monthly_goal': 3000000
    },
    'mundodeportivo': {
        'name': 'Mundo Deportivo',
        'icon': '🏆',
        'key_suffix': 'mundodeportivo',
        'domain': 'mundodeportivo.com',
        'credentials': 'damian_credentials_analytics_2025.json',
        'monthly_goal': 3000000
    },
    'natgeo': {
        'name': 'National Geographic',
        'icon': '🌍',
        'key_suffix': 'natgeo',
        'domain': 'nationalgeographic',
        'credentials': 'credentials_analytics_acceso_medios.json',
        'monthly_goal': 3000000
    },
    'bumeran': {
        'name': 'Bumeran',
        'icon': '💼',
        'key_suffix': 'bumeran',
        'domain': 'bumeran.com.ar',
        'credentials': 'credentials_analytics_acceso_medios.json',
        'monthly_goal': 3000000
    },
    'sancor': {
        'name': 'Sancor',
        'icon': '🏥',
        'key_suffix': 'sancor',
        'domain': 'sancorsalud.com.ar',
        'credentials': 'credentials_analytics_acceso_medios.json',
        'monthly_goal': 3000000
    },
    'vidae': {
        'name': 'Vidae',
        'icon': '💫',
        'key_suffix': 'vidae',
        'domain': 'vidae.com.ar',
        'credentials': 'credentials_analytics_acceso_medios.json',
        'monthly_goal': 3000000
    }
}

def read_template():
    """Lee el archivo template de okdiario"""
    with open('pages/redaccion-okdiario-20566.py', 'r', encoding='utf-8') as f:
        return f.read()

def apply_template_to_medio(template, medio_key, medio_config):
    """Aplica el template a un medio específico"""
    content = template

    # Reemplazar todas las referencias a okdiario
    content = content.replace('okdiario', medio_key)
    content = content.replace('OK Diario', medio_config['name'])
    content = content.replace('🗞️', medio_config['icon'])

    # Reemplazar credenciales si es diferente
    if medio_config['credentials'] != 'credentials_analytics_acceso_medios.json':
        content = content.replace(
            'credentials_file = "credentials_analytics_acceso_medios.json"',
            f'credentials_file = "{medio_config["credentials"]}"'
        )

    return content

def main():
    """Función principal"""
    print("🔧 Fixing redaccion pages...")

    # Leer template
    template = read_template()
    print("✓ Template loaded from redaccion-okdiario-20566.py")

    # Aplicar a cada medio (excepto okdiario)
    for medio_key, medio_config in MEDIOS.items():
        # Buscar archivo de redacción para este medio
        files = [f for f in os.listdir('pages') if f.startswith(f'redaccion-{medio_key}-')]

        if files:
            filename = files[0]
            filepath = os.path.join('pages', filename)

            print(f"\n📝 Processing {filename}...")

            # Aplicar template
            new_content = apply_template_to_medio(template, medio_key, medio_config)

            # Guardar
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(new_content)

            print(f"✓ Updated {filename}")
        else:
            print(f"⚠️  No redaccion file found for {medio_key}")

    print("\n✅ All redaccion pages updated!")

if __name__ == '__main__':
    main()
