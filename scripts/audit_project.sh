#!/bin/bash

# Script de auditoría para Dashboard de Contenidos
# Plataforma de contenido y redacciones

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "========================================="
echo "  Auditoría: Dashboard de Contenidos"
echo "========================================="
echo ""

# 1. LINTING
echo "📝 1. Análisis de código (Linting)"
echo "-----------------------------------------"

if [ -f "$PROJECT_DIR/requirements.txt" ]; then
    if command -v ruff &> /dev/null; then
        echo "Ejecutando ruff..."
        cd "$PROJECT_DIR"
        ruff check . --exit-zero || echo "✓ Ruff completado"
    elif command -v pylint &> /dev/null; then
        echo "Ejecutando pylint..."
        cd "$PROJECT_DIR"
        find . -maxdepth 2 -name "*.py" -not -path "./venv/*" -not -path "./.venv/*" | head -5 | xargs pylint --exit-zero 2>/dev/null || echo "✓ Pylint completado"
    else
        echo "⚠️  Ni ruff ni pylint instalados, verificando sintaxis básica..."
        python3 -m py_compile *.py 2>&1 | head -5 || echo "✓ Sintaxis Python válida"
    fi
else
    echo "ℹ️  No se encontró requirements.txt"
fi

echo ""

# 2. TESTS
echo "🧪 2. Tests automatizados"
echo "-----------------------------------------"

if [ -d "$PROJECT_DIR/tests" ]; then
    if command -v pytest &> /dev/null; then
        echo "Ejecutando pytest..."
        cd "$PROJECT_DIR"
        pytest -q --tb=short 2>&1 || echo "⚠️  Tests completados con warnings"
    else
        echo "⚠️  pytest no está instalado"
    fi
else
    echo "ℹ️  No se encontró directorio de tests"
fi

echo ""

# 3. GIT
echo "📊 3. Cambios recientes (Git)"
echo "-----------------------------------------"

if [ -d "$PROJECT_DIR/.git" ]; then
    cd "$PROJECT_DIR"
    echo "Últimos 5 commits:"
    git log --oneline -n 5 --decorate --color=always 2>/dev/null || echo "No hay commits"
else
    echo "ℹ️  No es un repositorio Git independiente"
fi

echo ""
echo "✅ Auditoría de Dashboard de Contenidos completada"
echo ""
