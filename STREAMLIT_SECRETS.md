# 🔑 Configuración de Secrets en Streamlit Cloud

## 📍 Instrucciones paso a paso:

1. **Ve a tu app en Streamlit Cloud**: https://share.streamlit.io/
2. **Click en tu app** > "Settings" ⚙️ > "Secrets" 🔐
3. **Pega esta configuración** y completa con tus valores reales:

```toml
[google_analytics]
clarin_property_id = "287171418"
ole_property_id = "151714594"
okdiario_property_id = "255037852"
spreadsheet_id = "1bT6C0VI_U7IEmI-ULPHJEvaOkL1mgCozWJIxdNavKBc"

# Para Clarín (si tienes credenciales separadas)
[google_oauth_acceso]
client_id = "TU_CLIENT_ID_CUENTA_1"
client_secret = "TU_CLIENT_SECRET_CUENTA_1"
refresh_token = "TU_REFRESH_TOKEN_CUENTA_1"

# Para Olé y OK Diario 
[google_oauth_medios]
client_id = "TU_CLIENT_ID_CUENTA_2"
client_secret = "TU_CLIENT_SECRET_CUENTA_2"
refresh_token = "TU_REFRESH_TOKEN_CUENTA_2"
```

## ⚠️ IMPORTANTE: 

### Refresh Token para `google_oauth_acceso`
Como no tienes refresh token para la primera cuenta, puedes:

**Opción 1: Usar solo una cuenta para todo**
```toml
[google_analytics]
clarin_property_id = "287171418"
ole_property_id = "151714594"
okdiario_property_id = "255037852"
spreadsheet_id = "1bT6C0VI_U7IEmI-ULPHJEvaOkL1mgCozWJIxdNavKBc"

# Solo configurar la cuenta que funciona
[google_oauth_acceso]
client_id = "USA_LOS_VALORES_DEL_ARCHIVO_credentials_analytics_acceso_medios.json"
client_secret = "USA_LOS_VALORES_DEL_ARCHIVO_credentials_analytics_acceso_medios.json"
refresh_token = "USA_LOS_VALORES_DEL_ARCHIVO_credentials_analytics_acceso_medios.json"

[google_oauth_medios]
client_id = "USA_LOS_VALORES_DEL_ARCHIVO_credentials_analytics_acceso_medios.json"
client_secret = "USA_LOS_VALORES_DEL_ARCHIVO_credentials_analytics_acceso_medios.json"
refresh_token = "USA_LOS_VALORES_DEL_ARCHIVO_credentials_analytics_acceso_medios.json"
```

**Opción 2: Generar refresh token nuevo**
Ejecuta `python generate_token.py` localmente para generar el refresh token de la primera cuenta.

## 🔄 Después de configurar:
1. Guarda los secrets
2. Redeploy la aplicación
3. Debería funcionar sin errores de autenticación