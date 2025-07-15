#!/bin/bash

# Script para ejecutar la aplicación Academic SaaS
echo "🚀 Iniciando Academic SaaS..."

# Activar entorno virtual
source academic_saas_env/bin/activate

# Verificar que las dependencias estén instaladas
if [ ! -f "academic_saas_env/bin/python" ]; then
    echo "❌ Error: Entorno virtual no encontrado"
    echo "Ejecuta: python3 -m venv academic_saas_env && source academic_saas_env/bin/activate && pip install -r requirements.txt"
    exit 1
fi

# Verificar variables de entorno
if [ ! -f ".env" ]; then
    echo "❌ Error: Archivo .env no encontrado"
    echo "Copia .env.example a .env y configura las variables"
    exit 1
fi

# Ejecutar migraciones si es necesario
echo "🔄 Ejecutando migraciones..."
python manage.py migrate

# Crear directorios necesarios
mkdir -p staticfiles
mkdir -p media

# Recopilar archivos estáticos
echo "📁 Recopilando archivos estáticos..."
python manage.py collectstatic --noinput

# Iniciar servidor
echo "✅ Aplicación lista!"
echo "📋 Panel de administración: http://localhost:8000/admin/"
echo "📖 Documentación API: http://localhost:8000/api/docs/"
echo "🔑 Usuario administrador: admin / admin123"
echo ""
echo "🌐 Iniciando servidor en http://localhost:8000..."

python manage.py runserver 0.0.0.0:8000