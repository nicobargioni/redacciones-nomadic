#!/usr/bin/env python3
"""
Script para probar la normalización de URLs de OKDiario
"""

import re
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
def normalize_url(url):
    """
    Normaliza una URL removiendo parámetros innecesarios, versiones AMP, 
    y estandarizando el formato específicamente para OKDiario.
    """
    if not url or url.strip() == "":
        return ""
    
    # Convertir a minúsculas para comparación
    url_lower = str(url).lower().strip()
    
    # Remover protocolo si existe
    url_clean = re.sub(r'^https?://', '', url_lower)
    
    # Remover www. si existe
    url_clean = re.sub(r'^www\.', '', url_clean)
    
    # Remover específicamente el dominio okdiario.com
    url_clean = re.sub(r'^okdiario\.com', '', url_clean)
    
    # Si no empieza con /, agregarlo (except para home que debe ser "/")
    if url_clean and not url_clean.startswith('/'):
        url_clean = '/' + url_clean
    
    # Remover fragmentos (#) antes de procesar paths
    if '#' in url_clean:
        url_clean = url_clean.split('#')[0]
    
    # Remover query parameters
    if '?' in url_clean:
        url_clean = url_clean.split('?')[0]
    
    # Remover /amp o .amp del final
    url_clean = re.sub(r'/amp/?$', '', url_clean)
    url_clean = re.sub(r'\.amp/?$', '', url_clean)
    
    # Colapsar dobles barras (//) en el path
    url_clean = re.sub(r'/+', '/', url_clean)
    
    # Remover trailing slash, EXCEPTO si la URL es solo "/"
    if url_clean != '/':
        url_clean = url_clean.rstrip('/')
    
    # Si quedó vacío, devolver "/"
    if not url_clean:
        url_clean = '/'
        
    return url_clean

# Casos de prueba
test_cases = [
    # Casos básicos
    "https://okdiario.com/economia/articulo-ejemplo",
    "https://www.okdiario.com/economia/articulo-ejemplo",
    "http://okdiario.com/economia/articulo-ejemplo",
    
    # Con trailing slash
    "https://okdiario.com/economia/articulo-ejemplo/",
    "https://okdiario.com/",
    
    # Con AMP
    "https://okdiario.com/economia/articulo-ejemplo/amp",
    "https://okdiario.com/economia/articulo-ejemplo/amp/",
    "https://okdiario.com/economia/articulo-ejemplo.amp",
    
    # Con parámetros de query
    "https://okdiario.com/economia/articulo-ejemplo?utm_source=facebook&utm_medium=social",
    "https://okdiario.com/economia/articulo-ejemplo?fbclid=12345&gclid=67890",
    
    # Con fragmentos
    "https://okdiario.com/economia/articulo-ejemplo#comentarios",
    
    # Casos edge
    "https://okdiario.com/economia//articulo-ejemplo",  # Dobles barras
    "HTTPS://OKDIARIO.COM/ECONOMIA/ARTICULO-EJEMPLO",  # Mayúsculas
    "https://okdiario.com/economia/articulo-ejemplo?utm=test#frag",  # Query + fragment
    
    # Solo home
    "https://okdiario.com",
    "https://www.okdiario.com/",
    
    # GA4 pagePaths (lo que viene de GA4)
    "/economia/articulo-ejemplo",
    "/economia/articulo-ejemplo/",
    "/economia/articulo-ejemplo/amp",
    "/",
]

print("=== PRUEBA DE NORMALIZACIÓN DE URLs ===\n")

for url in test_cases:
    normalized = normalize_url(url)
    print(f"Original:    {url}")
    print(f"Normalizada: {normalized}")
    print("-" * 50)

print("\n=== PRUEBA DE MERGE SIMULADO ===")
print("Sheet URLs vs GA4 pagePaths")

# Simular datos del Sheet
sheet_urls = [
    "https://okdiario.com/economia/articulo-1",
    "https://okdiario.com/deportes/futbol/articulo-2/",
    "https://www.okdiario.com/politica/articulo-3?utm_source=google",
]

# Simular pagePaths de GA4  
ga4_paths = [
    "/economia/articulo-1",
    "/deportes/futbol/articulo-2",
    "/politica/articulo-3",
    "/economia/articulo-otro",  # No debería hacer match
]

# Normalizar URLs del Sheet
sheet_normalized = [normalize_url(url) for url in sheet_urls]

# Simular normalización de GA4 (agregando dominio)
ga4_normalized = [normalize_url(f"okdiario.com{path}") for path in ga4_paths]

print("\nSheet URLs normalizadas:")
for i, (orig, norm) in enumerate(zip(sheet_urls, sheet_normalized)):
    print(f"  {i+1}: {orig} -> {norm}")

print("\nGA4 paths normalizadas:")
for i, (orig, norm) in enumerate(zip(ga4_paths, ga4_normalized)):
    print(f"  {i+1}: okdiario.com{orig} -> {norm}")

print("\nMatches encontrados:")
matches = []
for sheet_url in sheet_normalized:
    for ga4_url in ga4_normalized:
        if sheet_url == ga4_url:
            matches.append((sheet_url, ga4_url))
            print(f"  ✅ MATCH: {sheet_url}")

print(f"\nTotal matches: {len(matches)}")