#!/usr/bin/env python3
"""
Script para generar el string base64 de las credenciales de service account
"""
import base64
import json

# JSON de credenciales de service account
service_account_json = {
    "type": "service_account",
    "project_id": "damian-329018",
    "private_key_id": "",
    "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvAIBADANBgkqhkiG9w0BAQEFAASCBKYwggSiAgEAAoIBAQCz7OgsA5C5W+zR\nWDY9LWtuPh79s0DBy3t5mAL/4Oxbp0aBFjUe4XgYD90oyW5r8zE9ShufdJDV/TX6\nXV57GbkR1uqI7IROMW8gkEYg3IqBdEL3OGrV0lI19wCUvpvQr3vHOecnLPvfgihu\nBXrt6Cdlh7pAh7JU4cIqDzT6yhdl8eUbdMYBpDBngGumno9xdAiSGowj1RDUvv9n\n8C2pJ4/11BFFJNNEiPvxJu/GJirKR9fwW3RbCVO9HUNibswLHr0Qp0C7qcY+BoSk\nT9SWgdjyESkAQWAD0nKTIlq+tdJwA/5jhLRSWL3ktVZYeWDRVDf1xNzrCKbmIutb\nGAa7uUxnAgMBAAECggEAM3nuGtmSSFXSdTplmi8qc0n2l+L2/fr3gpxJD2gMd1Ru\nSXRPElyzfT7cqVSn8N6NEdnn+UDiRzbAgLbB1zpOxpnUVARG/hAKmShtx+0Q+2SF\n3DEZ777Sonnegq/d6GCsax1X0s996D5WztNmjjZDPzsLwHaSQNKuOFZNdArpktKd\nK1ErTi4TneDsgHx1ItRHbMl6tOAeeWTkpeLLjVoXMRfbioKxDjFEf3maAYpyO7pj\neQfYXQG8D8U1Vds3v5bVZJlWJuEHDAknd9FKYBGAhCr0Wz0pQO2tNTg1mG8KR1X/\nhOtwjy8x6eBcJhpYrjNe1fbX/kL8EKCozKeQKjgyMQKBgQDgO5Bead04rNY0Q7xc\nVDClTEgae9zKuWXzSVMgq9lXPPh1rpVK+ndrmYNymX4FG9tBvN12t/n4IlaTrTYK\nOLZ9O0CVokxEB9Op6iEUDeRc7NsVbmTBnG5CSEa6wBB7t7ESNPYBGxueyBv8+PSx\nX60ficRXTx2Mb5Z/eBDO7W/JBQKBgQDNamoP8oaU0zTK4KwcPbYne+B8i/Eg3f+X\nEpQvCfQTKMYG3vmK9AxWvhCIFN3VzpU63kcA3/PYbhzE6R/G49Iok3kJFe+SsL+L\njU6ywKZu3PDtxlMRgBBa9eM0gcOHuvgIyWaDAtA1IjFyaDHveHqLSGYFeJj14KAC\nFTaAf8aLewKBgCSIz+7yJL81OfluB+SrOvnTwfO+tqy5JGlNSyQJm/Hg10KlXWHI\nCWkYrBgh9ixy63h8g0DynOHXBnAtSp7DusgQvWcj+HUlKVGH+jfAQ7L4TIHjaLs6\n96QJDq0i2gyuU0V6J5LqjceDJzxCe+vigNygn8Lx+wiEreq671In0YzZAoGAPTUg\nNXBGucHVUT5xClk5FbrLwVDRoMGFjzZyATIuECduGk4GfWkK5C3uLx5Im5Ta0pe5\nAIG63xqwZ9wvI8xuqriGsDZhFIymBqcsdAcDkLU09STLS8OlG/V4pgSkhqUnkzav\n3QnRkIOHyFdTyc9UdHw2KhstONad1wELJG7uclECgYBcWzGXW3oRwCoyU2Nvq97N\nEqCtnqLVLU4YXIHGexJsJkofy4AvNWpABRUe5raJyEQTs7SWir58tViZ5Y2YV3XP\nM6CTsiYSBX9bE+mkuJs4jNUylKbikg6DocSItrlLnbzq1knMr0z9Z5Nsxuwixa/M\niAHF4vCUFABIT08sG9RVFQ==\n-----END PRIVATE KEY-----\n",
    "client_email": "gmail-admin@damian-329018.iam.gserviceaccount.com",
    "client_id": "",
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token"
}

# Convertir a JSON string
json_string = json.dumps(service_account_json)

# Codificar a base64
base64_string = base64.b64encode(json_string.encode('utf-8')).decode('utf-8')

print("=" * 80)
print("COPIAR ESTE STRING EN STREAMLIT SECRETS:")
print("=" * 80)
print()
print("[google_service_account_base64]")
print(f'credentials = "{base64_string}"')
print()
print("=" * 80)
print("AGREGAR ESTO A TUS SECRETS EXISTENTES")
print("=" * 80)