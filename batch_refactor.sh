#!/bin/bash
# Script para refactorizar todas las páginas de redacción

# Array de medios con sus nombres de archivos y nombres de display
declare -A medios
medios=(
    ["ole"]="Olé"
    ["elespanol"]="El Español"
    ["mundodeportivo"]="Mundo Deportivo"
    ["natgeo"]="National Geographic"
    ["vidae"]="Vidae"
    ["bumeran"]="Bumeran"
    ["sancor"]="Sancor"
)

# Template base (okdiario refactorizado)
TEMPLATE_FILE="/Users/nico/Documents/vscode/redacciones-nomadic/pages/redaccion-okdiario-20566.py"

# Función para refactorizar un archivo
refactor_page() {
    local medio_key=$1
    local medio_name=$2
    local file_path=$(ls /Users/nico/Documents/vscode/redacciones-nomadic/pages/redaccion-${medio_key}-*.py 2>/dev/null | head -1)

    if [ -z "$file_path" ]; then
        echo "❌ No se encontró archivo para $medio_name"
        return 1
    fi

    echo "🔧 Procesando: $medio_name ($file_path)"

    # Encontrar la línea donde comienza "# Métricas principales"
    START_LINE=$(grep -n "# Métricas principales" "$file_path" | head -1 | cut -d: -f1)

    # Encontrar la línea donde está el elif
    ELIF_LINE=$(grep -n "elif ga4_df is not None and not ga4_df.empty:" "$file_path" | head -1 | cut -d: -f1)

    if [ -z "$START_LINE" ] || [ -z "$ELIF_LINE" ]; then
        echo "  ⚠️  No se encontraron las líneas de referencia"
        return 1
    fi

    echo "  📍 Línea inicio: $START_LINE, Línea elif: $ELIF_LINE"

    # Crear archivo temporal
    local temp_file="/tmp/${medio_key}_new.py"

    # Copiar todo antes de la sección de métricas
    head -n $((START_LINE - 1)) "$file_path" > "$temp_file"

    # Copiar la sección refactorizada del template (líneas 229-843)
    # y reemplazar okdiario/OK Diario por el medio actual
    sed -n '229,843p' "$TEMPLATE_FILE" | \
        sed "s/okdiario/${medio_key}/g" | \
        sed "s/OK Diario/${medio_name}/g" >> "$temp_file"

    # Copiar todo desde el elif en adelante
    tail -n +$ELIF_LINE "$file_path" >> "$temp_file"

    # Reemplazar el archivo original
    cp "$temp_file" "$file_path"

    # Limpiar
    rm "$temp_file"

    echo "  ✅ Completado: $(wc -l < "$file_path") líneas"
    return 0
}

# Procesar cada medio
total=0
exitosos=0
fallidos=0

for medio_key in "${!medios[@]}"; do
    medio_name="${medios[$medio_key]}"
    ((total++))

    if refactor_page "$medio_key" "$medio_name"; then
        ((exitosos++))
    else
        ((fallidos++))
    fi
    echo
done

echo "=========================================="
echo "📊 RESUMEN"
echo "=========================================="
echo "Total:     $total"
echo "Exitosos:  $exitosos"
echo "Fallidos:  $fallidos"
echo "=========================================="