import re
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
import pandas as pd
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
import streamlit as st
from datetime import datetime, timedelta
import logging
import json
import base64
import pickle
import os
import hashlib

logger = logging.getLogger(__name__)

def decode_pickle_base64_credentials(encoded_string):
    """
    Decodifica credenciales desde string pickle+base64
    """
    try:
        # Decodificar base64 → bytes
        decoded_bytes = base64.b64decode(encoded_string.encode('utf-8'))
        
        # Despickle → dict
        credentials_data = pickle.loads(decoded_bytes)
        
        return credentials_data
    except Exception as e:
        logger.error(f"Error decodificando credenciales pickle+base64: {str(e)}")
        return None

def check_login(page_name=None):
    """
    Sistema de login independiente por página con control de acceso
    
    Args:
        page_name: Nombre del medio (ej: 'clarin', 'ole', 'mundodeportivo')
    
    Returns:
        True si el usuario está autenticado y tiene permisos, False si no
    """
    # Usar session_state específico por página para login independiente
    auth_key = f'authenticated_{page_name}' if page_name else 'authenticated'
    user_key = f'current_user_{page_name}' if page_name else 'current_user'
    
    # Inicializar estado de autenticación para esta página
    if auth_key not in st.session_state:
        st.session_state[auth_key] = False
    
    if not st.session_state[auth_key]:
        st.title("🔐 Acceso Requerido")
        if page_name:
            st.subheader(f"Dashboard de {page_name.title()}")
        st.markdown("---")
        
        # Obtener usuarios desde Streamlit secrets (OBLIGATORIO)
        try:
            if hasattr(st, 'secrets') and 'login_users' in st.secrets:
                users = dict(st.secrets['login_users'])
            else:
                st.error("🚨 **Error de configuración**")
                st.error("Faltan las credenciales de login en Streamlit secrets.")
                st.stop()
        except Exception as e:
            logger.error(f"Error cargando usuarios: {e}")
            st.error("🚨 Error crítico al cargar credenciales. Contacta al administrador.")
            st.stop()
        
        # Formulario de login
        with st.form(f"login_form_{page_name}"):
            username = st.text_input("Usuario")
            password = st.text_input("Contraseña", type="password")
            submitted = st.form_submit_button("Iniciar Sesión")
            
            if submitted:
                if username in users and password == users[username]:
                    # Verificar permisos de acceso
                    if page_name:
                        # Admin y redacciones pueden acceder a todo
                        if username == 'admin' or '_redaccion' in username:
                            st.session_state[auth_key] = True
                            st.session_state[user_key] = username
                            st.success("¡Login exitoso!")
                            st.rerun()
                        # Clientes solo pueden acceder a su página específica
                        elif f"{page_name}_cliente" == username:
                            st.session_state[auth_key] = True
                            st.session_state[user_key] = username
                            st.success("¡Login exitoso!")
                            st.rerun()
                        else:
                            st.error("❌ No tienes permisos para acceder a este dashboard")
                    else:
                        # Para páginas sin restricción específica
                        st.session_state[auth_key] = True
                        st.session_state[user_key] = username
                        st.success("¡Login exitoso!")
                        st.rerun()
                else:
                    st.error("Usuario o contraseña incorrectos")
        
        st.markdown("---")
        st.markdown("*Contacta al administrador para obtener credenciales de acceso*")
        return False
    
    # Mostrar info de usuario y logout en sidebar
    with st.sidebar:
        current_user = st.session_state.get(user_key, 'Desconocido')
        st.markdown(f"👤 **Usuario:** {current_user}")
        
        # Indicar tipo de acceso
        if current_user == 'admin':
            st.markdown("🔑 *Acceso administrativo*")
        elif '_redaccion' in current_user:
            st.markdown("📝 *Acceso redacción*")
        elif '_cliente' in current_user:
            st.markdown("👥 *Acceso cliente*")
            
        if st.button("🚪 Cerrar Sesión", key=f"logout_{page_name}"):
            st.session_state[auth_key] = False
            st.session_state[user_key] = None
            st.rerun()
    
    return True

def create_ga4_client(creds_data):
    """
    Construye el cliente GA4 usando build() como en tu función getAccesos()
    """
    creds = Credentials(
        token=creds_data.get('token'),
        refresh_token=creds_data.get('refresh_token'),
        id_token=creds_data.get('id_token'),
        token_uri=creds_data.get('token_uri'),
        client_id=creds_data.get('client_id'),
        client_secret=creds_data.get('client_secret'),
        scopes=creds_data.get('scopes', ['https://www.googleapis.com/auth/analytics.readonly'])
    )

    # Construir cliente GA4 usando build() como en getAccesos()
    ga4_client = build('analyticsdata', 'v1beta', credentials=creds)
    return ga4_client

def normalize_url(url):
    """
    Normaliza una URL removiendo parámetros innecesarios, versiones AMP, 
    y estandarizando el formato.
    """
    if pd.isna(url) or not url:
        return ""
    
    # Convertir a minúsculas para comparación
    url_lower = str(url).lower().strip()
    
    # Remover protocolo si existe
    url_clean = re.sub(r'^https?://', '', url_lower)
    
    # Remover www. si existe
    url_clean = re.sub(r'^www\.', '', url_clean)
    
    # Remover /amp o .amp del final
    url_clean = re.sub(r'/amp/?$', '', url_clean)
    url_clean = re.sub(r'\.amp/?$', '', url_clean)
    
    # Remover trailing slash
    url_clean = url_clean.rstrip('/')
    
    try:
        # Parse la URL para remover query parameters comunes de tracking
        if '?' in url_clean:
            base_url, query_string = url_clean.split('?', 1)
            # Parse query parameters
            parsed_qs = parse_qs(query_string)
            
            # Lista de parámetros a preservar (si necesitas algunos)
            params_to_keep = []
            
            # Filtrar solo los parámetros que queremos mantener
            filtered_params = {k: v for k, v in parsed_qs.items() 
                             if k in params_to_keep}
            
            # Si hay parámetros filtrados, reconstruir la URL
            if filtered_params:
                new_qs = urlencode(filtered_params, doseq=True)
                url_clean = f"{base_url}?{new_qs}"
            else:
                url_clean = base_url
    except:
        pass
    
    # Remover fragmentos (#)
    if '#' in url_clean:
        url_clean = url_clean.split('#')[0]
    
    return url_clean


def get_ga4_client_oauth(credentials_file, account_type="acceso"):
    """
    Crea un cliente de Google Analytics Data API v1beta usando OAuth2
    """
    try:
        logger.info(f"Creando cliente GA4 OAuth con account_type: {account_type}")
        
        # Caso especial para credenciales pickle+base64 de Damián
        if account_type == "damian":
            # Buscar credenciales en Streamlit secrets
            if hasattr(st, 'secrets') and 'damian_credentials_encoded' in st.secrets:
                encoded_string = st.secrets['damian_credentials_encoded']
                creds_data = decode_pickle_base64_credentials(encoded_string)
                if creds_data:
                    client = create_ga4_client(creds_data)
                    logger.info("Cliente GA4 creado con credenciales pickle+base64 de Damián")
                    return client
                else:
                    logger.error("No se pudieron decodificar las credenciales pickle+base64 de Damián")
                    return None
            else:
                logger.error("No se encontró damian_credentials_encoded en Streamlit secrets")
                return None
        else:
            # Obtener credenciales desde Streamlit secrets (caso normal)
            secret_key = f'google_oauth_{account_type}'
            if hasattr(st, 'secrets') and secret_key in st.secrets:
                creds_data = dict(st.secrets[secret_key])  # Convertir a dict
                client = create_ga4_client(creds_data)
                return client
            else:
                logger.error(f"No se encontró {secret_key} en Streamlit secrets")
                return None
            
    except Exception as e:
        logger.error(f"Error creando cliente GA4 con OAuth2: {e}")
        return None

@st.cache_data(ttl=300)
def get_ga4_data_with_country(property_id, credentials_file, start_date="7daysAgo", end_date="today", country_filter=None):
    """
    Obtiene datos de Google Analytics 4 para una propiedad específica con opción de filtrar por país
    """
    try:
        # Determinar qué tipo de cuenta usar según la propiedad
        if property_id == "255037852":  # OK Diario usa acceso_medios
            account_type = "acceso_medios"
        elif credentials_file == "damian_credentials_analytics_2025.json":  # Mundo Deportivo usa damian
            account_type = "damian"
        else:  # Clarín y Olé usan acceso
            account_type = "acceso"
        
        # Usar siempre Streamlit secrets
        if hasattr(st, 'secrets'):
            secret_key = f'google_oauth_{account_type}'
            if secret_key in st.secrets:
                logger.info(f"Usando credenciales {account_type} desde Streamlit secrets")
                client = get_ga4_client_oauth(credentials_file, account_type)
            else:
                logger.error(f"No se encontró la sección {secret_key} en Streamlit secrets")
                st.error(f"🔑 Falta configurar {secret_key} en Streamlit secrets")
                return None
        else:
            logger.error("No se encontraron credenciales válidas")
            st.error("🔑 No se encontraron credenciales. Configura Streamlit secrets.")
            return None
        
        if not client:
            logger.error("No se pudo crear el cliente GA4")
            return None
        
        # Definir dimensiones (incluyendo país si se especifica)
        dimensions = [
            {'name': 'pagePath'},
            {'name': 'date'},
            {'name': 'sessionSource'},
            {'name': 'sessionMedium'}
        ]
        
        # Agregar dimensión de país si se requiere filtro
        if country_filter:
            dimensions.append({'name': 'country'})
        
        # Crear el request body para la API v1beta
        request_body = {
            'dimensions': dimensions,
            'metrics': [
                {'name': 'sessions'},
                {'name': 'totalUsers'},
                {'name': 'screenPageViews'},
                {'name': 'averageSessionDuration'},
                {'name': 'bounceRate'},
                {'name': 'newUsers'},
                {'name': 'engagementRate'}
            ],
            'dateRanges': [{'startDate': start_date, 'endDate': end_date}],
            'limit': 10000
        }
        
        # Agregar filtro de país si se especifica
        if country_filter:
            request_body['dimensionFilter'] = {
                'filter': {
                    'fieldName': 'country',
                    'stringFilter': {
                        'value': country_filter,
                        'matchType': 'EXACT'
                    }
                }
            }
        
        # Ejecutar el reporte usando API v1beta
        logger.info(f"Consultando GA4 property {property_id}..." + (f" con filtro de país: {country_filter}" if country_filter else ""))
        response = client.properties().runReport(property=f"properties/{property_id}", body=request_body).execute()
        
        # Convertir a DataFrame usando formato API v1beta
        data = []
        if 'rows' in response:
            for row in response['rows']:
                row_data = {}
                # Dimensiones
                for i, dimension in enumerate(response['dimensionHeaders']):
                    row_data[dimension['name']] = row['dimensionValues'][i]['value']
                # Métricas
                for i, metric in enumerate(response['metricHeaders']):
                    value = row['metricValues'][i]['value']
                    # Convertir a número si es posible
                    try:
                        if '.' in value:
                            row_data[metric['name']] = float(value)
                        else:
                            row_data[metric['name']] = int(value)
                    except:
                        row_data[metric['name']] = value
                data.append(row_data)
        
        df = pd.DataFrame(data)
        
        # Convertir fecha
        if 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'], format='%Y%m%d')
        
        logger.info(f"GA4 datos obtenidos: {len(df)} filas" + (f" (filtrado por {country_filter})" if country_filter else ""))
        return df
        
    except Exception as e:
        logger.error(f"Error obteniendo datos de GA4: {e}")
        
        # Mensajes de error más específicos
        error_msg = str(e).lower()
        if 'invalid_grant' in error_msg:
            st.error("🔐 Error de autenticación: El token de acceso ha expirado o es inválido.")
            st.warning("""
            **Solución requerida:**
            1. Regenerar los tokens OAuth2 para Google Analytics
            2. Actualizar `google_oauth_medios` en Streamlit secrets
            3. Verificar que la cuenta tiene acceso a la property ID
            """)
        elif '403' in str(e) or 'forbidden' in error_msg:
            st.error("🚫 Error de permisos: No tienes acceso a esta propiedad de GA4.")
        elif '404' in str(e) or 'not found' in error_msg:
            st.error("❌ Error: Property ID no encontrada en GA4.")
        else:
            st.error(f"Error al obtener datos de GA4: {str(e)}")
        
        # Mensajes de ayuda específicos
        if "403" in str(e) or "permission" in str(e).lower():
            st.warning("""
            ⚠️ **Error de permisos**
            
            Para OAuth2:
            1. Verifica que la cuenta Google asociada tenga acceso a la propiedad GA4
            2. Intenta regenerar el token de acceso
            
            Para cuenta de servicio:
            1. Agrega el email de la cuenta de servicio en GA4
            2. Admin > Property Access Management > Add users
            """)
        elif "401" in str(e):
            st.warning("""
            ⚠️ **Token expirado o inválido**
            
            El token de acceso puede haber expirado. 
            Necesitas regenerar el token OAuth2.
            """)
        
        return None

@st.cache_data(ttl=300)
def get_ga4_data(property_id, credentials_file, start_date="7daysAgo", end_date="today"):
    """
    Obtiene datos de Google Analytics 4 para una propiedad específica
    Determina automáticamente qué cuenta usar según la propiedad
    """
    try:
        # Determinar qué tipo de cuenta usar según la propiedad
        if property_id == "255037852":  # OK Diario usa acceso_medios
            account_type = "acceso_medios"
        elif credentials_file == "damian_credentials_analytics_2025.json":  # Mundo Deportivo usa damian
            account_type = "damian"
        else:  # Clarín y Olé usan acceso
            account_type = "acceso"
        
        # Usar siempre Streamlit secrets
        if hasattr(st, 'secrets'):
            secret_key = f'google_oauth_{account_type}'
            if secret_key in st.secrets:
                logger.info(f"Usando credenciales {account_type} desde Streamlit secrets")
                client = get_ga4_client_oauth(credentials_file, account_type)
            else:
                logger.error(f"No se encontró la sección {secret_key} en Streamlit secrets")
                st.error(f"🔑 Falta configurar {secret_key} en Streamlit secrets")
                return None
        else:
            logger.error("No se encontraron credenciales válidas")
            st.error("🔑 No se encontraron credenciales. Configura Streamlit secrets.")
            return None
        
        if not client:
            logger.error("No se pudo crear el cliente GA4")
            return None
        
        # Crear el request body para la API v1beta
        request_body = {
            'dimensions': [
                {'name': 'pagePath'},
                {'name': 'date'},
                {'name': 'sessionSource'},
                {'name': 'sessionMedium'}
            ],
            'metrics': [
                {'name': 'sessions'},
                {'name': 'totalUsers'},
                {'name': 'screenPageViews'},
                {'name': 'averageSessionDuration'},
                {'name': 'bounceRate'},
                {'name': 'newUsers'},
                {'name': 'engagementRate'}
            ],
            'dateRanges': [{'startDate': start_date, 'endDate': end_date}],
            'limit': 10000
        }
        
        # Ejecutar el reporte usando API v1beta
        logger.info(f"Consultando GA4 property {property_id}...")
        response = client.properties().runReport(property=f"properties/{property_id}", body=request_body).execute()
        
        # Convertir a DataFrame usando formato API v1beta
        data = []
        if 'rows' in response:
            for row in response['rows']:
                row_data = {}
                # Dimensiones
                for i, dimension in enumerate(response['dimensionHeaders']):
                    row_data[dimension['name']] = row['dimensionValues'][i]['value']
                # Métricas
                for i, metric in enumerate(response['metricHeaders']):
                    value = row['metricValues'][i]['value']
                    # Convertir a número si es posible
                    try:
                        if '.' in value:
                            row_data[metric['name']] = float(value)
                        else:
                            row_data[metric['name']] = int(value)
                    except:
                        row_data[metric['name']] = value
                data.append(row_data)
        
        df = pd.DataFrame(data)
        
        # Convertir fecha
        if 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'], format='%Y%m%d')
        
        logger.info(f"GA4 datos obtenidos: {len(df)} filas")
        return df
        
    except Exception as e:
        logger.error(f"Error obteniendo datos de GA4: {e}")
        
        # Mensajes de error más específicos
        error_msg = str(e).lower()
        if 'invalid_grant' in error_msg:
            st.error("🔐 Error de autenticación: El token de acceso ha expirado o es inválido.")
            st.warning("""
            **Solución requerida:**
            1. Regenerar los tokens OAuth2 para Google Analytics
            2. Actualizar `google_oauth_medios` en Streamlit secrets
            3. Verificar que la cuenta tiene acceso a la property ID
            """)
        elif '403' in str(e) or 'forbidden' in error_msg:
            st.error("🚫 Error de permisos: No tienes acceso a esta propiedad de GA4.")
        elif '404' in str(e) or 'not found' in error_msg:
            st.error("❌ Error: Property ID no encontrada en GA4.")
        else:
            st.error(f"Error al obtener datos de GA4: {str(e)}")
        
        # Mensajes de ayuda específicos
        if "403" in str(e) or "permission" in str(e).lower():
            st.warning("""
            ⚠️ **Error de permisos**
            
            Para OAuth2:
            1. Verifica que la cuenta Google asociada tenga acceso a la propiedad GA4
            2. Intenta regenerar el token de acceso
            
            Para cuenta de servicio:
            1. Agrega el email de la cuenta de servicio en GA4
            2. Admin > Property Access Management > Add users
            """)
        elif "401" in str(e):
            st.warning("""
            ⚠️ **Token expirado o inválido**
            
            El token de acceso puede haber expirado. 
            Necesitas regenerar el token OAuth2.
            """)
        
        return None

@st.cache_data(ttl=300)
def load_google_sheet_data():
    """
    Carga los datos del Google Sheet privado usando cuenta de servicio con impersonación
    """
    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
        
        # Obtener credentials desde Streamlit secrets
        if hasattr(st, 'secrets') and 'google_service_account_base64' in st.secrets:
            import base64
            import json
            
            # Decodificar el JSON desde base64
            try:
                # Obtener el string base64 (acceder al campo específico)
                credentials_base64 = st.secrets['google_service_account_base64']['credentials']
                
                
                # Decodificar base64 a bytes
                credentials_bytes = base64.b64decode(credentials_base64)
                
                # Convertir bytes a string y luego a dict
                service_account_info = json.loads(credentials_bytes.decode('utf-8'))
                
                logger.info("Service account credentials decodificadas desde base64 exitosamente")
                
            except Exception as e:
                st.error(f"Error decodificando credenciales base64: {str(e)}")
                raise
            
            try:
                credentials = service_account.Credentials.from_service_account_info(
                    service_account_info,
                    scopes=['https://www.googleapis.com/auth/spreadsheets.readonly']
                )
            except Exception as e:
                st.error(f"ERROR creando credenciales: {str(e)}")
                st.error(f"Tipo de error: {type(e).__name__}")
                raise
            
            # Obtener spreadsheet_id desde secrets
            spreadsheet_id = st.secrets['google_analytics'].get('spreadsheet_id', '1n-jYrNH_S_uLzhCJhTzLfEJn_nnrsU2H5jkxNjtwO6Q')
            
            # Crear cliente de Google Sheets
            service = build('sheets', 'v4', credentials=credentials)
            
            # Leer datos del sheet
            result = service.spreadsheets().values().get(
                spreadsheetId=spreadsheet_id,
                range='A:Z'  # Leer todas las columnas
            ).execute()
            
            values = result.get('values', [])
            if not values:
                logger.warning("No se encontraron datos en el Google Sheet")
                return pd.DataFrame()
            
            # Convertir a DataFrame
            df = pd.DataFrame(values[1:], columns=values[0])  # Primera fila como headers
            
        else:
            # Fallback al método público anterior
            spreadsheet_id = '1n-jYrNH_S_uLzhCJhTzLfEJn_nnrsU2H5jkxNjtwO6Q'
            public_url = f'https://docs.google.com/spreadsheets/d/{spreadsheet_id}/export?format=csv'
            df = pd.read_csv(public_url)
        
        # Procesar fechas si existen
        date_columns = [col for col in df.columns if 'date' in col.lower() or 'fecha' in col.lower()]
        for col in date_columns:
            try:
                df[col] = pd.to_datetime(df[col], errors='coerce')
            except:
                pass
        
        logger.info(f"Google Sheet cargado: {len(df)} filas")
        return df
        
    except Exception as e:
        logger.error(f"Error al cargar Google Sheet: {e}")
        st.error(f"Error al cargar el spreadsheet: {str(e)}")
        return None

def filter_media_urls(df, domain):
    """
    Filtra un DataFrame para incluir solo URLs de un dominio específico
    """
    if df is None or df.empty:
        return pd.DataFrame()
    
    # La columna 'url' ya está identificada en el Sheet
    if 'url' in df.columns:
        mask = df['url'].astype(str).str.contains(domain, case=False, na=False)
        filtered_df = df[mask].copy()
        logger.info(f"Filtradas {len(filtered_df)} URLs para {domain}")
        return filtered_df
    
    return pd.DataFrame()

def merge_sheets_with_ga4(sheets_df, ga4_df, domain):
    """
    Mergea los datos del Google Sheet con los datos de GA4
    """
    if sheets_df is None or sheets_df.empty or ga4_df is None or ga4_df.empty:
        return pd.DataFrame()
    
    # Normalizar URLs en ambos DataFrames
    if 'url' not in sheets_df.columns:
        st.warning("No se encontró columna 'url' en los datos del Google Sheet")
        return pd.DataFrame()
    
    # Crear columna de URL normalizada
    sheets_df['url_normalized'] = sheets_df['url'].apply(normalize_url)
    
    # Normalizar pagePath de GA4 
    try:
        ga4_df['url_normalized'] = ga4_df['pagePath'].apply(lambda x: normalize_url(f"{domain}{x}"))
    except Exception as e:
        logger.error(f"Error normalizando URLs de GA4: {e}")
        return pd.DataFrame()
    
    # Agrupar GA4 por URL normalizada para obtener métricas agregadas
    # Verificar qué columnas están disponibles y son numéricas
    agg_dict = {}
    
    # Columnas para suma
    sum_columns = ['sessions', 'totalUsers', 'screenPageViews', 'newUsers']
    for col in sum_columns:
        if col in ga4_df.columns:
            agg_dict[col] = 'sum'
    
    # Columnas para promedio (necesitan ser numéricas)
    mean_columns = ['averageSessionDuration', 'bounceRate', 'engagementRate']
    for col in mean_columns:
        if col in ga4_df.columns:
            # Convertir a numérico, reemplazando errores con NaN
            ga4_df[col] = pd.to_numeric(ga4_df[col], errors='coerce')
            agg_dict[col] = 'mean'
    
    ga4_grouped = ga4_df.groupby('url_normalized').agg(agg_dict).reset_index()
    
    # Hacer el merge
    merged_df = sheets_df.merge(
        ga4_grouped,
        on='url_normalized',
        how='left',
        suffixes=('', '_ga4')
    )
    
    # Llenar NaN con 0 para métricas
    metric_columns = ['sessions', 'totalUsers', 'screenPageViews', 
                     'averageSessionDuration', 'bounceRate', 'newUsers', 'engagementRate']
    for col in metric_columns:
        if col in merged_df.columns:
            merged_df[col] = merged_df[col].fillna(0)
    
    logger.info(f"Merge completado: {len(merged_df)} filas con datos combinados")
    return merged_df

def create_media_config():
    """
    Retorna la configuración de cada medio usando Streamlit secrets o valores por defecto
    """
    # Intentar obtener Property IDs desde secrets
    try:
        if hasattr(st, 'secrets') and 'google_analytics' in st.secrets:
            ga_config = st.secrets['google_analytics']
            return {
                'clarin': {
                    'name': 'Clarín',
                    'domain': 'clarin.com',
                    'property_id': ga_config.get('clarin_property_id', '287171418'),
                    'icon': '📰',
                    'color': '#1e88e5'
                },
                'ole': {
                    'name': 'Olé',
                    'domain': 'ole.com.ar',
                    'property_id': ga_config.get('ole_property_id', '151714594'),
                    'icon': '⚽',
                    'color': '#43a047'
                },
                'okdiario': {
                    'name': 'OK Diario',
                    'domain': 'okdiario.com',
                    'property_id': ga_config.get('okdiario_property_id', '255037852'),
                    'icon': '🗞️',
                    'color': '#e53935'
                },
                'elespanol': {
                    'name': 'El Español',
                    'domain': 'elespanol.com',
                    'property_id': ga_config.get('elespanol_property_id', '000000000'),
                    'icon': '🇪🇸',
                    'color': '#ff6b00'
                },
                'natgeo': {
                    'name': 'National Geographic',
                    'domain': 'nationalgeographic',  # Buscar todas las variantes
                    'property_id': ga_config.get('natgeo_property_id', '000000000'),
                    'icon': '🌍',
                    'color': '#ffcc02'
                },
                'mundodeportivo': {
                    'name': 'Mundo Deportivo',
                    'domain': 'mundodeportivo.com',
                    'property_id': ga_config.get('mundodeportivo_property_id', '000000000'),
                    'icon': '🏆',
                    'color': '#0066cc'
                },
                'vidae': {
                    'name': 'Vidae',
                    'domain': 'vidae.com.ar',
                    'property_id': ga_config.get('vidae_property_id', '000000000'),
                    'icon': '💫',
                    'color': '#9c27b0'
                },
                'bumeran': {
                    'name': 'Bumeran',
                    'domain': 'bumeran.com.ar',
                    'property_id': ga_config.get('bumeran_property_id', '000000000'),
                    'icon': '💼',
                    'color': '#00a651'
                },
                'sancor': {
                    'name': 'Sancor',
                    'domain': 'sancorsalud.com.ar',
                    'property_id': ga_config.get('sancor_property_id', '000000000'),
                    'icon': '🏥',
                    'color': '#0d47a1'
                }
            }
    except:
        pass
    
    # Valores por defecto
    return {
        'clarin': {
            'name': 'Clarín',
            'domain': 'clarin.com',
            'property_id': '287171418',
            'icon': '📰',
            'color': '#1e88e5'
        },
        'ole': {
            'name': 'Olé',
            'domain': 'ole.com.ar',
            'property_id': '151714594',
            'icon': '⚽',
            'color': '#43a047'
        },
        'okdiario': {
            'name': 'OK Diario',
            'domain': 'okdiario.com',
            'property_id': '255037852',
            'icon': '🗞️',
            'color': '#e53935'
        },
        'elespanol': {
            'name': 'El Español',
            'domain': 'elespanol.com',
            'property_id': '000000000',
            'icon': '🇪🇸',
            'color': '#ff6b00'
        },
        'natgeo': {
            'name': 'National Geographic',
            'domain': 'nationalgeographic',  # Buscar todas las variantes
            'property_id': '000000000',
            'icon': '🌍',
            'color': '#ffcc02'
        },
        'mundodeportivo': {
            'name': 'Mundo Deportivo',
            'domain': 'mundodeportivo.com',
            'property_id': '416839948',
            'icon': '🏆',
            'color': '#0066cc'
        },
        'vidae': {
            'name': 'Vidae',
            'domain': 'vidae.com.ar',
            'property_id': '000000000',
            'icon': '💫',
            'color': '#9c27b0'
        },
        'bumeran': {
            'name': 'Bumeran',
            'domain': 'bumeran.com.ar',
            'property_id': '000000000',
            'icon': '💼',
            'color': '#00a651'
        },
        'sancor': {
            'name': 'Sancor',
            'domain': 'sancorsalud.com.ar',
            'property_id': '000000000',
            'icon': '🏥',
            'color': '#0d47a1'
        }
    }