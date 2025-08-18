import re
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
import pandas as pd
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import (
    RunReportRequest,
    Dimension,
    Metric,
    DateRange
)
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
import streamlit as st
from datetime import datetime, timedelta
import logging
import json
import os

logger = logging.getLogger(__name__)

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

def get_oauth2_credentials(credentials_file=None, account_type="acceso"):
    """
    Crea credenciales OAuth2 desde Streamlit secrets o archivo local
    account_type: "acceso" para Clarín, "medios" para Olé/OK Diario
    """
    try:
        # Intentar primero con Streamlit secrets
        secret_key = f'google_oauth_{account_type}'
        if hasattr(st, 'secrets') and secret_key in st.secrets:
            logger.info(f"Usando credenciales desde Streamlit secrets: {secret_key}")
            oauth_config = st.secrets[secret_key]
            
            credentials = Credentials(
                token=oauth_config.get('access_token'),
                refresh_token=oauth_config['refresh_token'],
                token_uri='https://oauth2.googleapis.com/token',
                client_id=oauth_config['client_id'],
                client_secret=oauth_config['client_secret'],
                scopes=['https://www.googleapis.com/auth/analytics.readonly']
            )
            
            # Refrescar si es necesario
            if credentials.expired and credentials.refresh_token:
                logger.info("Refrescando token OAuth2...")
                credentials.refresh(Request())
            
            return credentials
            
        # Fallback a archivo local para desarrollo
        elif credentials_file and os.path.exists(credentials_file):
            logger.info(f"Usando credenciales desde archivo: {credentials_file}")
            with open(credentials_file, 'r') as f:
                token_data = json.load(f)
            
            credentials = Credentials(
                token=token_data.get('token'),
                refresh_token=token_data.get('refresh_token'),
                token_uri=token_data.get('token_uri', 'https://oauth2.googleapis.com/token'),
                client_id=token_data.get('client_id'),
                client_secret=token_data.get('client_secret'),
                scopes=token_data.get('scopes', ['https://www.googleapis.com/auth/analytics.readonly'])
            )
            
            if credentials.expired and credentials.refresh_token:
                logger.info("Refrescando token OAuth2...")
                credentials.refresh(Request())
                
                # Guardar el nuevo token
                token_data['token'] = credentials.token
                with open(credentials_file, 'w') as f:
                    json.dump(token_data, f, indent=2)
            
            return credentials
        else:
            logger.error("No se encontraron credenciales válidas")
            return None
            
    except Exception as e:
        logger.error(f"Error creando credenciales OAuth2: {e}")
        return None

def get_ga4_client_oauth(credentials_file, account_type="acceso"):
    """
    Crea un cliente de Google Analytics Data API v1beta usando OAuth2
    """
    try:
        credentials = get_oauth2_credentials(credentials_file, account_type)
        if not credentials:
            return None
            
        client = BetaAnalyticsDataClient(credentials=credentials)
        return client
    except Exception as e:
        logger.error(f"Error creando cliente GA4 con OAuth2: {e}")
        return None

@st.cache_data(ttl=300)
def get_ga4_data(property_id, credentials_file, start_date="7daysAgo", end_date="today"):
    """
    Obtiene datos de Google Analytics 4 para una propiedad específica
    Determina automáticamente qué cuenta usar según la propiedad
    """
    try:
        # Determinar qué tipo de cuenta usar según la propiedad
        account_type = "acceso"  # Por defecto para Clarín
        if property_id in ["151714594", "255037852"]:  # Olé y OK Diario
            account_type = "medios"
        
        # Intentar primero con archivo local (como antes)
        if credentials_file and os.path.exists(credentials_file):
            with open(credentials_file, 'r') as f:
                cred_data = json.load(f)
            
            # Si tiene refresh_token, es OAuth2
            if 'refresh_token' in cred_data:
                logger.info("Usando credenciales OAuth2 desde archivo")
                client = get_ga4_client_oauth(credentials_file, account_type)
            else:
                # Si no, asumimos que es cuenta de servicio
                logger.info("Usando credenciales de cuenta de servicio")
                from google.oauth2 import service_account
                credentials = service_account.Credentials.from_service_account_file(
                    credentials_file,
                    scopes=["https://www.googleapis.com/auth/analytics.readonly"]
                )
                client = BetaAnalyticsDataClient(credentials=credentials)
        
        # Fallback a Streamlit secrets
        elif hasattr(st, 'secrets'):
            logger.info(f"Usando credenciales {account_type} desde Streamlit secrets")
            client = get_ga4_client_oauth(credentials_file, account_type)
        else:
            logger.error("No se encontraron credenciales válidas")
            return None
        
        if not client:
            logger.error("No se pudo crear el cliente GA4")
            return None
        
        # Construir la request
        request = RunReportRequest(
            property=f"properties/{property_id}",
            dimensions=[
                Dimension(name="pagePath"),
                Dimension(name="date"),
                Dimension(name="sessionSource"),
                Dimension(name="sessionMedium")
            ],
            metrics=[
                Metric(name="sessions"),
                Metric(name="totalUsers"),
                Metric(name="screenPageViews"),
                Metric(name="averageSessionDuration"),
                Metric(name="bounceRate"),
                Metric(name="newUsers"),
                Metric(name="engagementRate")
            ],
            date_ranges=[DateRange(start_date=start_date, end_date=end_date)],
            limit=10000
        )
        
        # Ejecutar el reporte
        logger.info(f"Consultando GA4 property {property_id}...")
        response = client.run_report(request)
        
        # Convertir a DataFrame
        data = []
        for row in response.rows:
            row_data = {}
            # Dimensiones
            for i, dimension in enumerate(response.dimension_headers):
                row_data[dimension.name] = row.dimension_values[i].value
            # Métricas
            for i, metric in enumerate(response.metric_headers):
                value = row.metric_values[i].value
                # Convertir a número si es posible
                try:
                    if '.' in value:
                        row_data[metric.name] = float(value)
                    else:
                        row_data[metric.name] = int(value)
                except:
                    row_data[metric.name] = value
            data.append(row_data)
        
        df = pd.DataFrame(data)
        
        # Convertir fecha
        if 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'], format='%Y%m%d')
        
        logger.info(f"GA4 datos obtenidos: {len(df)} filas")
        return df
        
    except Exception as e:
        logger.error(f"Error obteniendo datos de GA4: {e}")
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
    Carga los datos del Google Sheet público usando Streamlit secrets o valor por defecto
    """
    try:
        # Obtener spreadsheet_id desde secrets o usar valor por defecto
        if hasattr(st, 'secrets') and 'google_analytics' in st.secrets:
            spreadsheet_id = st.secrets['google_analytics'].get('spreadsheet_id', '1bT6C0VI_U7IEmI-ULPHJEvaOkL1mgCozWJIxdNavKBc')
        else:
            spreadsheet_id = '1bT6C0VI_U7IEmI-ULPHJEvaOkL1mgCozWJIxdNavKBc'
            
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
    ga4_grouped = ga4_df.groupby('url_normalized').agg({
        'sessions': 'sum',
        'totalUsers': 'sum',
        'screenPageViews': 'sum',
        'averageSessionDuration': 'mean',
        'bounceRate': 'mean',
        'newUsers': 'sum',
        'engagementRate': 'mean'
    }).reset_index()
    
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
        }
    }