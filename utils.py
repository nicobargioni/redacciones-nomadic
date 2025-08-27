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
import os

logger = logging.getLogger(__name__)

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
    url_clean = re.sub(r'(/amp|\.amp)/?$', '', url_clean)
    
    # Remover slash final
    url_clean = url_clean.rstrip('/')
    
    # Remover parámetros de tracking comunes
    patterns_to_remove = [
        r'\?utm_[^&]*(&utm_[^&]*)*$',  # Solo parámetros UTM
        r'[?&]fbclid=[^&]*',            # Facebook click ID
        r'[?&]gclid=[^&]*',             # Google click ID
        r'[?&]ref=[^&]*',               # Referencias
        r'#.*$'                         # Fragmentos
    ]
    
    for pattern in patterns_to_remove:
        url_clean = re.sub(pattern, '', url_clean)
    
    # Limpiar múltiples ? o &
    url_clean = re.sub(r'[?&]+', '?', url_clean)
    url_clean = url_clean.rstrip('?&')
    
    return url_clean

def parse_date_range(date_str):
    """
    Convierte una fecha en formato string a formato de fecha para GA4
    """
    if date_str == "today":
        return datetime.now().strftime('%Y-%m-%d')
    elif date_str.endswith("daysAgo"):
        days = int(date_str.replace("daysAgo", ""))
        date = datetime.now() - timedelta(days=days)
        return date.strftime('%Y-%m-%d')
    else:
        return date_str

def get_ga4_client_oauth(credentials_file, account_type="acceso"):
    """
    Crea un cliente de Google Analytics Data API v1beta usando OAuth2
    """
    try:
        logger.info(f"Creando cliente GA4 OAuth con account_type: {account_type}")
        
        # Obtener credenciales desde Streamlit secrets
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
            logger.error("No se encontraron Streamlit secrets")
            return None
        
        if client is None:
            logger.error("No se pudo crear el cliente GA4")
            return None
        
        # Parsear las fechas
        start_date_parsed = parse_date_range(start_date)
        end_date_parsed = parse_date_range(end_date)
        
        # Crear request para GA4 Data API
        request_body = {
            'dateRanges': [{
                'startDate': start_date_parsed,
                'endDate': end_date_parsed
            }],
            'dimensions': [
                {'name': 'date'},
                {'name': 'pagePath'},
                {'name': 'sessionSource'},
                {'name': 'sessionMedium'},
                {'name': 'deviceCategory'}
            ],
            'metrics': [
                {'name': 'sessions'},
                {'name': 'totalUsers'},
                {'name': 'newUsers'},
                {'name': 'screenPageViews'},
                {'name': 'averageSessionDuration'},
                {'name': 'bounceRate'},
                {'name': 'engagementRate'}
            ],
            'limit': 100000,
            'orderBys': [{
                'desc': True,
                'metric': {'metricName': 'sessions'}
            }]
        }
        
        # Agregar filtro de país si se especifica
        if country_filter and country_filter != "Todos los países":
            request_body['dimensionFilter'] = {
                'filter': {
                    'fieldName': 'country',
                    'stringFilter': {
                        'value': country_filter,
                        'matchType': 'EXACT'
                    }
                }
            }
        
        # Hacer la solicitud a GA4
        response = client.properties().runReport(
            property=f'properties/{property_id}',
            body=request_body
        ).execute()
        
        # Procesar respuesta
        if 'rows' not in response:
            logger.warning(f"No hay datos disponibles para el período especificado con filtro de país: {country_filter}")
            return pd.DataFrame()
        
        # Convertir a DataFrame
        data = []
        for row in response['rows']:
            row_data = {}
            for i, dimension in enumerate(row['dimensionValues']):
                dim_name = request_body['dimensions'][i]['name']
                row_data[dim_name] = dimension['value']
            for i, metric in enumerate(row['metricValues']):
                metric_name = request_body['metrics'][i]['name']
                value = metric['value']
                # Convertir métricas numéricas
                if metric_name in ['sessions', 'totalUsers', 'newUsers', 'screenPageViews']:
                    row_data[metric_name] = int(value) if value != '(not set)' else 0
                else:
                    row_data[metric_name] = float(value) if value != '(not set)' else 0.0
            data.append(row_data)
        
        df = pd.DataFrame(data)
        
        # Convertir columna date a datetime
        if 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'], format='%Y%m%d')
        
        logger.info(f"Datos de GA4 obtenidos exitosamente: {len(df)} filas con filtro de país: {country_filter}")
        return df
        
    except Exception as e:
        if 'PERMISSION_DENIED' in str(e):
            logger.error(f"Error de permisos para property_id {property_id}")
            st.error("🚫 Error de permisos: No tienes acceso a esta propiedad de GA4.")
            st.markdown("""
            ### ⚠️ Error de permisos
            
            **Para OAuth2:**
            - Verifica que la cuenta Google asociada tenga acceso a la propiedad GA4
            - Intenta regenerar el token de acceso
            
            **Para cuenta de servicio:**
            - Agrega el email de la cuenta de servicio en GA4
            - Admin > Property Access Management > Add users
            """)
        else:
            logger.error(f"Error obteniendo datos de GA4 con filtro de país: {e}")
            st.error(f"❌ Error al conectar con GA4: {str(e)}")
        
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
            logger.error("No se encontraron Streamlit secrets")
            return None
        
        if client is None:
            logger.error("No se pudo crear el cliente GA4")
            return None
        
        # Parsear las fechas
        start_date_parsed = parse_date_range(start_date)
        end_date_parsed = parse_date_range(end_date)
        
        # Crear request para GA4 Data API
        request_body = {
            'dateRanges': [{
                'startDate': start_date_parsed,
                'endDate': end_date_parsed
            }],
            'dimensions': [
                {'name': 'date'},
                {'name': 'pagePath'},
                {'name': 'sessionSource'},
                {'name': 'sessionMedium'},
                {'name': 'deviceCategory'}
            ],
            'metrics': [
                {'name': 'sessions'},
                {'name': 'totalUsers'},
                {'name': 'newUsers'},
                {'name': 'screenPageViews'},
                {'name': 'averageSessionDuration'},
                {'name': 'bounceRate'},
                {'name': 'engagementRate'}
            ],
            'limit': 100000,
            'orderBys': [{
                'desc': True,
                'metric': {'metricName': 'sessions'}
            }]
        }
        
        # Hacer la solicitud a GA4
        response = client.properties().runReport(
            property=f'properties/{property_id}',
            body=request_body
        ).execute()
        
        # Procesar respuesta
        if 'rows' not in response:
            logger.warning("No hay datos disponibles para el período especificado")
            return pd.DataFrame()
        
        # Convertir a DataFrame
        data = []
        for row in response['rows']:
            row_data = {}
            for i, dimension in enumerate(row['dimensionValues']):
                dim_name = request_body['dimensions'][i]['name']
                row_data[dim_name] = dimension['value']
            for i, metric in enumerate(row['metricValues']):
                metric_name = request_body['metrics'][i]['name']
                value = metric['value']
                # Convertir métricas numéricas
                if metric_name in ['sessions', 'totalUsers', 'newUsers', 'screenPageViews']:
                    row_data[metric_name] = int(value) if value != '(not set)' else 0
                else:
                    row_data[metric_name] = float(value) if value != '(not set)' else 0.0
            data.append(row_data)
        
        df = pd.DataFrame(data)
        
        # Convertir columna date a datetime
        if 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'], format='%Y%m%d')
        
        logger.info(f"Datos de GA4 obtenidos exitosamente: {len(df)} filas")
        return df
        
    except Exception as e:
        if 'PERMISSION_DENIED' in str(e):
            logger.error(f"Error de permisos para property_id {property_id}")
            st.error("🚫 Error de permisos: No tienes acceso a esta propiedad de GA4.")
            st.markdown("""
            ### ⚠️ Error de permisos
            
            **Para OAuth2:**
            - Verifica que la cuenta Google asociada tenga acceso a la propiedad GA4
            - Intenta regenerar el token de acceso
            
            **Para cuenta de servicio:**
            - Agrega el email de la cuenta de servicio en GA4
            - Admin > Property Access Management > Add users
            """)
        else:
            logger.error(f"Error obteniendo datos de GA4: {e}")
            st.error(f"❌ Error al conectar con GA4: {str(e)}")
        
        return None

@st.cache_data(ttl=300)
def load_google_sheet_data():
    """
    Carga los datos del Google Sheet público usando Streamlit secrets o valor por defecto
    NOTA: Temporalmente usando método público hasta resolver problema de service account
    """
    try:
        # TEMPORAL: Usar método público
        spreadsheet_id = '1n-jYrNH_S_uLzhCJhTzLfEJn_nnrsU2H5jkxNjtwO6Q'
        if hasattr(st, 'secrets') and 'google_analytics' in st.secrets:
            spreadsheet_id = st.secrets['google_analytics'].get('spreadsheet_id', '1n-jYrNH_S_uLzhCJhTzLfEJn_nnrsU2H5jkxNjtwO6Q')
        
        # Verificar si el Sheet es público, si no lo es, el usuario debe compartirlo
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
        logger.error(f"Error al cargar el spreadsheet: {e}")
        st.error(f"Error al cargar el spreadsheet: {e}")
        st.info("""
        Para solucionar este error:
        1. Asegúrate de que el Google Sheet sea público (Compartir > Cualquiera con el enlace puede ver)
        2. O configura una cuenta de servicio con los permisos adecuados
        """)
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
        return sheets_df
    
    # Normalizar URLs en ambos DataFrames
    sheets_df['url_normalized'] = sheets_df['url'].apply(normalize_url)
    ga4_df['url_normalized'] = ga4_df['pagePath'].apply(lambda x: normalize_url(f"{domain}{x}"))
    
    # Agrupar GA4 por URL normalizada y sumar métricas
    ga4_grouped = ga4_df.groupby('url_normalized').agg({
        'sessions': 'sum',
        'totalUsers': 'sum',
        'newUsers': 'sum',
        'screenPageViews': 'sum',
        'averageSessionDuration': 'mean',
        'bounceRate': 'mean',
        'engagementRate': 'mean'
    }).reset_index()
    
    # Hacer el merge
    merged_df = sheets_df.merge(
        ga4_grouped,
        on='url_normalized',
        how='left'
    )
    
    # Llenar valores NaN con 0 para métricas
    metrics_columns = ['sessions', 'totalUsers', 'newUsers', 'screenPageViews', 
                      'averageSessionDuration', 'bounceRate', 'engagementRate']
    
    for col in metrics_columns:
        if col in merged_df.columns:
            merged_df[col] = merged_df[col].fillna(0)
    
    logger.info(f"Merge completado: {len(merged_df)} filas totales")
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
                    'domain': 'nationalgeographic.com.es',
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
            'domain': 'nationalgeographic.com.es',
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