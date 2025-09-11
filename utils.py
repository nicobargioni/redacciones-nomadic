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

def format_growth_percentage(growth_pct, growth_absolute):
    """
    Formatea el porcentaje de crecimiento manejando valores infinitos
    """
    if growth_pct == float('inf'):
        return f"Nuevo (+{growth_absolute:,})"
    elif growth_pct == float('-inf'):
        return f"-100% ({growth_absolute:+,})"
    else:
        return f"{growth_pct:+.1f}% ({growth_absolute:+,})"

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

def check_login(page_name=None, page_type=None):
    """
    Sistema de login independiente por página con control de acceso
    
    Args:
        page_name: Nombre del medio (ej: 'clarin', 'ole', 'mundodeportivo')
        page_type: Tipo de página ('redaccion' o 'cliente')
    
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
            if page_type == 'redaccion':
                st.subheader(f"Dashboard de {page_name.title()} - Redacción")
            elif page_type == 'cliente':
                st.subheader(f"Dashboard de {page_name.title()} - Cliente")
            else:
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
                    # Verificar permisos de acceso según el tipo de página
                    if page_name and page_type:
                        # Admin puede acceder a todo
                        if username == 'admin':
                            st.session_state[auth_key] = True
                            st.session_state[user_key] = username
                            st.success("¡Login exitoso!")
                            st.rerun()
                        # Páginas de redacción: solo usuarios de redacción
                        elif page_type == 'redaccion':
                            if '_redaccion' in username:
                                st.session_state[auth_key] = True
                                st.session_state[user_key] = username
                                st.success("¡Login exitoso!")
                                st.rerun()
                            else:
                                st.error("❌ Solo usuarios de redacción pueden acceder a esta página")
                        # Páginas de cliente: solo el cliente específico
                        elif page_type == 'cliente':
                            if f"{page_name}_cliente" == username:
                                st.session_state[auth_key] = True
                                st.session_state[user_key] = username
                                st.success("¡Login exitoso!")
                                st.rerun()
                            else:
                                st.error("❌ No tienes permisos para acceder a este dashboard de cliente")
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
            'limit': 100000
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
            # Formatear fecha como dd/mm/yyyy para mostrar
            df['date_formatted'] = df['date'].dt.strftime('%d/%m/%Y')
        
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
            'limit': 100000
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
            # Formatear fecha como dd/mm/yyyy para mostrar
            df['date_formatted'] = df['date'].dt.strftime('%d/%m/%Y')
        
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
                # Formatear fechas como dd/mm/yyyy para mostrar
                df[f"{col}_formatted"] = df[col].dt.strftime('%d/%m/%Y')
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
    
    # Formatear fechas de publicación
    date_columns = ['datePub', 'fecha_publicacion', 'fecha', 'date']
    for col in date_columns:
        if col in merged_df.columns:
            try:
                # Convertir a datetime si no lo está ya
                merged_df[col] = pd.to_datetime(merged_df[col], errors='coerce')
                # Formatear como dd/mm/yyyy
                merged_df[col] = merged_df[col].dt.strftime('%d/%m/%Y')
            except Exception as e:
                logger.warning(f"Error formateando fecha en columna {col}: {e}")
                continue
    
    # Llenar NaN con 0 para métricas
    metric_columns = ['sessions', 'totalUsers', 'screenPageViews', 
                     'averageSessionDuration', 'bounceRate', 'newUsers', 'engagementRate']
    for col in metric_columns:
        if col in merged_df.columns:
            merged_df[col] = merged_df[col].fillna(0)
    
    logger.info(f"Merge completado: {len(merged_df)} filas con datos combinados")
    return merged_df

@st.cache_data(ttl=300)
def get_ga4_pageviews_data(property_id, credentials_file, period="month"):
    """
    Obtiene datos de pageviews para el período especificado
    period: "month" (mes actual), "week" (última semana), "total" (últimos 90 días)
    """
    try:
        # Determinar fechas según el período
        from datetime import datetime, timedelta
        today = datetime.now()
        
        if period == "month":
            # Mes actual
            start_date = today.replace(day=1).strftime("%Y-%m-%d")
            end_date = today.strftime("%Y-%m-%d")
        elif period == "week":
            # Últimos 7 días
            start_date = (today - timedelta(days=7)).strftime("%Y-%m-%d")
            end_date = today.strftime("%Y-%m-%d")
        else:  # total
            # Últimos 90 días
            start_date = (today - timedelta(days=90)).strftime("%Y-%m-%d")
            end_date = today.strftime("%Y-%m-%d")
        
        # Determinar qué tipo de cuenta usar
        if property_id == "255037852":  # OK Diario
            account_type = "acceso_medios"
        elif credentials_file == "damian_credentials_analytics_2025.json":  # Mundo Deportivo
            account_type = "damian"
        else:
            account_type = "acceso"
        
        # Usar Streamlit secrets
        if hasattr(st, 'secrets'):
            secret_key = f'google_oauth_{account_type}'
            if secret_key in st.secrets:
                credentials_data = st.secrets[secret_key]
                credentials_dict = dict(credentials_data)
            else:
                return None
        else:
            return None
        
        # Crear cliente
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build
        
        creds = Credentials(
            token=credentials_dict.get('token'),
            refresh_token=credentials_dict.get('refresh_token'),
            client_id=credentials_dict.get('client_id'),
            client_secret=credentials_dict.get('client_secret'),
            token_uri="https://oauth2.googleapis.com/token"
        )
        
        client = build('analyticsdata', 'v1beta', credentials=creds)
        
        # Request para pageviews totales y por página (excluyendo home)
        request_body = {
            'dimensions': [
                {'name': 'pagePath'}
            ],
            'metrics': [
                {'name': 'screenPageViews'}
            ],
            'dateRanges': [{'startDate': start_date, 'endDate': end_date}],
            'limit': 100000
        }
        
        response = client.properties().runReport(
            property=f"properties/{property_id}", 
            body=request_body
        ).execute()
        
        # Procesar respuesta
        total_pageviews = 0
        non_home_pageviews = 0
        non_home_pages = 0
        
        if 'rows' in response:
            for row in response['rows']:
                page_path = row['dimensionValues'][0]['value']
                pageviews = int(row['metricValues'][0]['value'])
                
                total_pageviews += pageviews
                
                # Excluir home (/, /index, etc.)
                if page_path not in ['/', '/index', '/index.html', '/home']:
                    non_home_pageviews += pageviews
                    non_home_pages += 1
        
        avg_pageviews_per_page = non_home_pageviews / non_home_pages if non_home_pages > 0 else 0
        
        return {
            'total_pageviews': total_pageviews,
            'non_home_pageviews': non_home_pageviews,
            'non_home_pages': non_home_pages,
            'avg_pageviews_per_page': avg_pageviews_per_page
        }
        
    except Exception as e:
        logger.error(f"Error obteniendo pageviews de GA4: {e}")
        return None

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

@st.cache_data(ttl=300)
def get_ga4_growth_data(property_id, credentials_file, comparison_type="day", sheets_urls=None):
    """
    Obtiene datos de crecimiento comparando períodos t vs t-1, filtrando solo URLs del Sheet
    comparison_type: "day", "week", "month", "90days", "custom"
    sheets_urls: Lista de URLs normalizadas del Google Sheet para filtrar
    """
    from datetime import datetime, timedelta
    
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
                return None
        else:
            return None
        
        if not client:
            return None
        
        today = datetime.now()
        
        # Definir períodos según el tipo de comparación
        if comparison_type == "day":
            current_start = today - timedelta(days=1)  # Ayer
            current_end = today - timedelta(days=1)    # Ayer
            previous_start = today - timedelta(days=2)  # Anteayer
            previous_end = today - timedelta(days=2)    # Anteayer
            period_name = "Día"
        elif comparison_type == "week":
            current_start = today - timedelta(days=7)   # Última semana
            current_end = today - timedelta(days=1)     # Hasta ayer
            previous_start = today - timedelta(days=14) # Semana anterior
            previous_end = today - timedelta(days=8)    # Hasta hace 8 días
            period_name = "Semana"
        elif comparison_type == "month":
            # Mes actual vs mes anterior
            current_start = today.replace(day=1)        # Inicio mes actual
            current_end = today                         # Hoy
            # Mes anterior
            if today.month == 1:
                previous_start = datetime(today.year - 1, 12, 1)
                previous_end = datetime(today.year, 1, 1) - timedelta(days=1)
            else:
                previous_start = datetime(today.year, today.month - 1, 1)
                previous_end = datetime(today.year, today.month, 1) - timedelta(days=1)
            period_name = "Mes"
        elif comparison_type == "90days":
            current_start = today - timedelta(days=90)  # Últimos 90 días
            current_end = today                         # Hoy
            previous_start = today - timedelta(days=180) # 90 días anteriores
            previous_end = today - timedelta(days=91)   # Hasta hace 91 días
            period_name = "90 días"
        else:
            return None
        
        # Función para obtener datos de un período
        def get_period_data(start_date, end_date):
            request_body = {
                'dimensions': [
                    {'name': 'pagePath'}
                ],
                'metrics': [
                    {'name': 'screenPageViews'},
                    {'name': 'sessions'},
                    {'name': 'totalUsers'}
                ],
                'dateRanges': [{'startDate': start_date.strftime("%Y-%m-%d"), 
                               'endDate': end_date.strftime("%Y-%m-%d")}],
                'limit': 100000
            }
            
            response = client.properties().runReport(
                property=f"properties/{property_id}", 
                body=request_body
            ).execute()
            
            # Procesar respuesta
            total_pageviews = 0
            total_sessions = 0
            total_users = 0
            
            if 'rows' in response and sheets_urls:
                # Si tenemos URLs del Sheet, filtrar solo esas
                for row in response['rows']:
                    page_path = row['dimensionValues'][0]['value']
                    
                    # Buscar si este pagePath está en alguna de las URLs del Sheet
                    # Comparar el path completo ya que sheets_urls ya está normalizado
                    match_found = False
                    for sheet_url in sheets_urls:
                        # Verificar si el pagePath está contenido en la URL del Sheet
                        if page_path in sheet_url or sheet_url.endswith(page_path.lstrip('/')):
                            match_found = True
                            break
                    
                    if match_found:
                        pageviews = int(row['metricValues'][0]['value'])
                        sessions = int(row['metricValues'][1]['value'])
                        users = int(row['metricValues'][2]['value'])
                        
                        total_pageviews += pageviews
                        total_sessions += sessions
                        total_users += users
            elif 'rows' in response and not sheets_urls:
                # Si no hay URLs del Sheet, usar todos los datos (fallback)
                for row in response['rows']:
                    pageviews = int(row['metricValues'][0]['value'])
                    sessions = int(row['metricValues'][1]['value'])
                    users = int(row['metricValues'][2]['value'])
                    
                    total_pageviews += pageviews
                    total_sessions += sessions
                    total_users += users
            
            return {
                'pageviews': total_pageviews,
                'sessions': total_sessions,
                'users': total_users
            }
        
        # Obtener datos de ambos períodos
        current_data = get_period_data(current_start, current_end)
        previous_data = get_period_data(previous_start, previous_end)
        
        # Calcular crecimiento
        growth_data = {}
        for metric in ['pageviews', 'sessions', 'users']:
            current_value = current_data[metric]
            previous_value = previous_data[metric]
            
            if previous_value > 0:
                growth_percentage = ((current_value - previous_value) / previous_value) * 100
            elif previous_value == 0 and current_value > 0:
                growth_percentage = float('inf')  # Crecimiento infinito (desde 0)
            elif previous_value == 0 and current_value == 0:
                growth_percentage = 0  # Sin cambio (ambos períodos en 0)
            else:  # previous_value > 0 and current_value == 0
                growth_percentage = -100  # Decrecimiento total
            
            growth_data[metric] = {
                'current': current_value,
                'previous': previous_value,
                'growth_percentage': growth_percentage,
                'growth_absolute': current_value - previous_value
            }
        
        return {
            'period_name': period_name,
            'current_period': f"{current_start.strftime('%d/%m/%Y')} - {current_end.strftime('%d/%m/%Y')}",
            'previous_period': f"{previous_start.strftime('%d/%m/%Y')} - {previous_end.strftime('%d/%m/%Y')}",
            'data': growth_data
        }
        
    except Exception as e:
        logger.error(f"Error obteniendo datos de crecimiento: {e}")
        return None

@st.cache_data(ttl=300)
def get_ga4_growth_data_custom(property_id, credentials_file, current_start, current_end, previous_start, previous_end, sheets_urls=None):
    """
    Obtiene datos de crecimiento para períodos personalizados, filtrando solo URLs del Sheet
    sheets_urls: Lista de URLs normalizadas del Google Sheet para filtrar
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
                client = get_ga4_client_oauth(credentials_file, account_type)
            else:
                return None
        else:
            return None
        
        if not client:
            return None
        
        # Función para obtener datos de un período
        def get_period_data(start_date, end_date):
            request_body = {
                'dimensions': [
                    {'name': 'pagePath'}
                ],
                'metrics': [
                    {'name': 'screenPageViews'},
                    {'name': 'sessions'},
                    {'name': 'totalUsers'}
                ],
                'dateRanges': [{'startDate': start_date.strftime("%Y-%m-%d"), 
                               'endDate': end_date.strftime("%Y-%m-%d")}],
                'limit': 100000
            }
            
            response = client.properties().runReport(
                property=f"properties/{property_id}", 
                body=request_body
            ).execute()
            
            # Procesar respuesta
            total_pageviews = 0
            total_sessions = 0
            total_users = 0
            
            if 'rows' in response and sheets_urls:
                # Si tenemos URLs del Sheet, filtrar solo esas
                for row in response['rows']:
                    page_path = row['dimensionValues'][0]['value']
                    
                    # Buscar si este pagePath está en alguna de las URLs del Sheet
                    # Comparar el path completo ya que sheets_urls ya está normalizado
                    match_found = False
                    for sheet_url in sheets_urls:
                        # Verificar si el pagePath está contenido en la URL del Sheet
                        if page_path in sheet_url or sheet_url.endswith(page_path.lstrip('/')):
                            match_found = True
                            break
                    
                    if match_found:
                        pageviews = int(row['metricValues'][0]['value'])
                        sessions = int(row['metricValues'][1]['value'])
                        users = int(row['metricValues'][2]['value'])
                        
                        total_pageviews += pageviews
                        total_sessions += sessions
                        total_users += users
            elif 'rows' in response and not sheets_urls:
                # Si no hay URLs del Sheet, usar todos los datos (fallback)
                for row in response['rows']:
                    pageviews = int(row['metricValues'][0]['value'])
                    sessions = int(row['metricValues'][1]['value'])
                    users = int(row['metricValues'][2]['value'])
                    
                    total_pageviews += pageviews
                    total_sessions += sessions
                    total_users += users
            
            return {
                'pageviews': total_pageviews,
                'sessions': total_sessions,
                'users': total_users
            }
        
        # Obtener datos de ambos períodos
        current_data = get_period_data(current_start, current_end)
        previous_data = get_period_data(previous_start, previous_end)
        
        # Calcular crecimiento
        growth_data = {}
        for metric in ['pageviews', 'sessions', 'users']:
            current_value = current_data[metric]
            previous_value = previous_data[metric]
            
            if previous_value > 0:
                growth_percentage = ((current_value - previous_value) / previous_value) * 100
            elif previous_value == 0 and current_value > 0:
                growth_percentage = float('inf')  # Crecimiento infinito (desde 0)
            elif previous_value == 0 and current_value == 0:
                growth_percentage = 0  # Sin cambio (ambos períodos en 0)
            else:  # previous_value > 0 and current_value == 0
                growth_percentage = -100  # Decrecimiento total
            
            growth_data[metric] = {
                'current': current_value,
                'previous': previous_value,
                'growth_percentage': growth_percentage,
                'growth_absolute': current_value - previous_value
            }
        
        return {
            'period_name': 'Personalizado',
            'current_period': f"{current_start.strftime('%d/%m/%Y')} - {current_end.strftime('%d/%m/%Y')}",
            'previous_period': f"{previous_start.strftime('%d/%m/%Y')} - {previous_end.strftime('%d/%m/%Y')}",
            'data': growth_data
        }
        
    except Exception as e:
        logger.error(f"Error obteniendo datos de crecimiento personalizado: {e}")
        return None

@st.cache_data(ttl=300)
def get_ga4_historical_data(property_id, credentials_file, start_date, end_date, time_granularity="day", sheets_urls=None, domain=None):
    """
    Obtiene datos históricos de GA4 para análisis temporal, filtrando solo URLs del Sheet
    
    Args:
        property_id: ID de la propiedad GA4
        credentials_file: Archivo de credenciales
        start_date: Fecha de inicio (datetime)
        end_date: Fecha de fin (datetime)
        time_granularity: "day", "week", "month"
        sheets_urls: Lista de URLs normalizadas del Google Sheet para filtrar
        domain: Dominio del medio para normalización de URLs
    
    Returns:
        DataFrame con datos históricos por fecha y página
    """
    from datetime import datetime, timedelta
    import pandas as pd
    
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
                client = get_ga4_client_oauth(credentials_file, account_type)
            else:
                return None
        else:
            return None
        
        if not client:
            return None
        
        # Configurar dimensiones según granularidad temporal
        dimensions = [
            {'name': 'pagePath'},
            {'name': 'date'}
        ]
        
        # Crear el request body
        request_body = {
            'dimensions': dimensions,
            'metrics': [
                {'name': 'screenPageViews'},
                {'name': 'sessions'},
                {'name': 'totalUsers'}
            ],
            'dateRanges': [{'startDate': start_date.strftime("%Y-%m-%d"), 
                           'endDate': end_date.strftime("%Y-%m-%d")}],
            'limit': 1000000,
            'orderBys': [{'dimension': {'dimensionName': 'date'}}]
        }
        
        response = client.properties().runReport(
            property=f"properties/{property_id}", 
            body=request_body
        ).execute()
        
        # Procesar respuesta
        data = []
        
        if 'rows' in response:
            for row in response['rows']:
                page_path = row['dimensionValues'][0]['value']
                date_str = row['dimensionValues'][1]['value']
                
                # Buscar si este pagePath está en alguna de las URLs del Sheet
                # Comparar el path completo ya que sheets_urls ya está normalizado
                match_found = False
                if sheets_urls:
                    for sheet_url in sheets_urls:
                        # Verificar si el pagePath está contenido en la URL del Sheet
                        if page_path in sheet_url or sheet_url.endswith(page_path.lstrip('/')):
                            match_found = True
                            break
                else:
                    match_found = True  # Si no hay filtro, incluir todo
                
                if match_found:
                    pageviews = int(row['metricValues'][0]['value'])
                    sessions = int(row['metricValues'][1]['value'])
                    users = int(row['metricValues'][2]['value'])
                    
                    data.append({
                        'pagePath': page_path,
                        'url_normalized': normalize_url(f"{domain}{page_path}") if domain else page_path,  # Normalizar con dominio completo
                        'date': datetime.strptime(date_str, '%Y%m%d'),
                        'pageviews': pageviews,
                        'sessions': sessions,
                        'users': users
                    })
        
        df = pd.DataFrame(data)
        
        logger.info(f"GA4 historical response: {len(response.get('rows', []))} rows from GA4")
        if sheets_urls:
            logger.info(f"Filtering by {len(sheets_urls)} sheet URLs")
        logger.info(f"Final dataframe: {len(df)} rows after filtering")
        
        if not df.empty:
            # Aplicar granularidad temporal
            if time_granularity == "week":
                df['period'] = df['date'].dt.to_period('W').dt.start_time
                df['period_formatted'] = df['period'].dt.strftime('%d/%m/%Y')
            elif time_granularity == "month":
                df['period'] = df['date'].dt.to_period('M').dt.start_time
                df['period_formatted'] = df['period'].dt.strftime('%d/%m/%Y')
            else:  # day
                df['period'] = df['date']
                df['period_formatted'] = df['period'].dt.strftime('%d/%m/%Y')
            
            logger.info(f"Datos históricos obtenidos: {len(df)} filas, granularidad: {time_granularity}")
        
        return df
        
    except Exception as e:
        logger.error(f"Error obteniendo datos históricos de GA4: {e}")
        return None