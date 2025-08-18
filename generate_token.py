#!/usr/bin/env python3
"""
Script para generar refresh token desde un archivo de cliente OAuth
"""

import json
import os
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

# Scopes necesarios para Analytics
SCOPES = ['https://www.googleapis.com/auth/analytics.readonly']

def generate_refresh_token(client_secrets_file, output_file):
    """
    Genera un refresh token desde un archivo de cliente OAuth
    """
    try:
        # Crear el flujo OAuth
        flow = InstalledAppFlow.from_client_secrets_file(
            client_secrets_file, 
            SCOPES
        )
        
        # Ejecutar el flujo de autorización local
        print("Iniciando flujo de autorizacion...")
        print("Se abrira tu navegador para autorizar la aplicacion")
        
        # Esto abrirá el navegador
        credentials = flow.run_local_server(port=0)
        
        # Crear el archivo de credenciales con tokens
        token_data = {
            "token": credentials.token,
            "refresh_token": credentials.refresh_token,
            "token_uri": credentials.token_uri,
            "client_id": credentials.client_id,
            "client_secret": credentials.client_secret,
            "scopes": credentials.scopes
        }
        
        # Guardar en archivo
        with open(output_file, 'w') as f:
            json.dump(token_data, f, indent=2)
        
        print(f"Credenciales guardadas en: {output_file}")
        print(f"Refresh token generado: {credentials.refresh_token}")
        
        return token_data
        
    except Exception as e:
        print(f"Error generando token: {e}")
        return None

if __name__ == "__main__":
    # Archivos
    client_file = "C:\\Users\\nicob\\Downloads\\analytics_acceso.json"
    output_file = "credentials_analytics_acceso_generated.json"
    
    if not os.path.exists(client_file):
        print(f"No se encontro el archivo: {client_file}")
        exit(1)
    
    print("Generando refresh token para analytics_acceso.json...")
    result = generate_refresh_token(client_file, output_file)
    
    if result:
        print("\nPara Streamlit secrets, usa estos valores:")
        print(f"client_id = \"{result['client_id']}\"")
        print(f"client_secret = \"{result['client_secret']}\"")
        print(f"refresh_token = \"{result['refresh_token']}\"")
    else:
        print("No se pudo generar el token")