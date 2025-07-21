#!/bin/bash

# Script para iniciar el entorno local con conexión a la base de datos dev

echo "🔗 Iniciando túnel SSH para PostgreSQL..."

# Verificar si ya existe un túnel
if lsof -Pi :5433 -sTCP:LISTEN -t >/dev/null ; then
    echo "⚠️  El túnel SSH ya está activo en el puerto 5433"
else
    # Crear túnel SSH
    ssh -o IdentitiesOnly=yes -i ~/.ssh/academic-saas-github-actions \
        -L 5433:localhost:5432 -N -f ec2-user@52.20.22.173
    
    if [ $? -eq 0 ]; then
        echo "✅ Túnel SSH creado exitosamente (puerto local 5433 -> remoto 5432)"
    else
        echo "❌ Error al crear el túnel SSH"
        exit 1
    fi
fi

# Esperar un poco para que el túnel se establezca
sleep 2

echo "🧪 Probando conexión a la base de datos..."

# Probar conexión con Python
python3 -c "
import psycopg2
try:
    conn = psycopg2.connect(
        host='localhost',
        port='5433',
        database='academic_saas_dev',
        user='admin',
        password='admin123'
    )
    cursor = conn.cursor()
    cursor.execute('SELECT current_database(), current_user;')
    result = cursor.fetchone()
    print(f'✅ Conexión exitosa: Database={result[0]}, User={result[1]}')
    conn.close()
except Exception as e:
    print(f'❌ Error de conexión: {e}')
    exit 1
"

if [ $? -eq 0 ]; then
    echo "🚀 Iniciando servidor Django..."
    python manage.py runserver 0.0.0.0:8000
else
    echo "❌ No se pudo conectar a la base de datos"
    exit 1
fi