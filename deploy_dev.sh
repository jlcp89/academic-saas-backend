#!/bin/bash

# ================================================================
# Academic SaaS - Backend Development Deployment Script
# ================================================================
# Este script despliega el backend (Django) en el entorno de desarrollo
# sin Docker, usando Python directo y Gunicorn con PM2 para process management.
# 
# Uso: 
#   ./deploy_dev.sh              # Instalación inteligente de dependencias
#   ./deploy_dev.sh --force-deps # Forzar reinstalación de dependencias
# ================================================================

set -e  # Exit on any error

# Variables de configuración
FORCE_DEPS=false
if [[ "$1" == "--force-deps" ]]; then
    FORCE_DEPS=true
fi

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Función para logging
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# ================================================================
# VERIFICACIONES PREVIAS
# ================================================================

log_info "🚀 Iniciando deployment de Backend en DEV..."
log_info "============================================"

# Verificar Python
if ! command -v python3 &> /dev/null; then
    log_error "Python3 no está instalado"
    exit 1
fi

# Verificar PostgreSQL
if ! command -v psql &> /dev/null; then
    log_info "PostgreSQL no está instalado. Instalando..."
    sudo yum update -y
    sudo yum install -y postgresql postgresql-server postgresql-devel
    sudo postgresql-setup initdb
    sudo systemctl enable postgresql
    sudo systemctl start postgresql
fi

# Verificar Nginx
if ! command -v nginx &> /dev/null; then
    log_info "Nginx no está instalado. Instalando..."
    sudo yum update -y
    sudo yum install -y nginx
    sudo systemctl enable nginx
fi

# ================================================================
# CONFIGURACIÓN DE NGINX
# ================================================================

log_info "🌐 Configurando Nginx..."

# Hacer backup de la configuración existente
if [ -f /etc/nginx/nginx.conf ]; then
    sudo cp /etc/nginx/nginx.conf /etc/nginx/nginx.conf.backup-$(date +%Y%m%d-%H%M%S)
fi

# Copiar configuración de nginx corregida para NextAuth
if [ -f "nginx-dev-nextauth-fixed.conf" ]; then
    log_info "Aplicando configuración de nginx corregida (NextAuth fix)..."
    sudo cp nginx-dev-nextauth-fixed.conf /etc/nginx/nginx.conf
elif [ -f "nginx-dev.conf" ]; then
    log_info "Aplicando configuración de nginx de desarrollo..."
    sudo cp nginx-dev.conf /etc/nginx/nginx.conf
else
    log_warning "No se encontró configuración de nginx personalizada, usando configuración por defecto"
fi

# Validar configuración de nginx
if sudo nginx -t; then
    log_success "✅ Configuración de nginx válida"
else
    log_error "❌ Error en configuración de nginx"
    exit 1
fi

# Verificar Poetry
if ! command -v poetry &> /dev/null; then
    log_info "Poetry no está instalado. Instalando..."
    curl -sSL https://install.python-poetry.org | python3 -
    export PATH="$HOME/.local/bin:$PATH"
fi

# ================================================================
# CONFIGURACIÓN DEL BACKEND
# ================================================================

log_info "📦 Configurando Backend (Django)..."

# Verificar Poetry y dependencias
if [ ! -f "pyproject.toml" ]; then
    log_error "pyproject.toml no encontrado. Este archivo es requerido para garantizar consistencia."
    log_error "Asegúrate de que el repositorio incluya pyproject.toml con las dependencias exactas."
    exit 1
fi

log_info "Configurando Poetry para el proyecto..."

# Configurar Poetry para usar un directorio virtual local
poetry config virtualenvs.in-project true

# Instalar dependencias con Poetry (garantiza versiones exactas via poetry.lock)
if [ "$FORCE_DEPS" = true ] || [ ! -f ".deps_installed" ] || [ "pyproject.toml" -nt ".deps_installed" ] || [ "poetry.lock" -nt ".deps_installed" ]; then
    log_info "Instalando/actualizando dependencias con Poetry..."
    log_info "Poetry garantiza las mismas versiones exactas que el entorno local"
    poetry install --only=main --no-dev
    touch .deps_installed
else
    log_info "Dependencias del backend ya están actualizadas ✓"
fi

# Configurar base de datos PostgreSQL
log_info "Configurando base de datos PostgreSQL..."

# Crear usuario y base de datos PostgreSQL
sudo -u postgres psql << 'EOF'
CREATE USER admin WITH PASSWORD 'admin123';
CREATE DATABASE academic_saas_dev OWNER admin;
GRANT ALL PRIVILEGES ON DATABASE academic_saas_dev TO admin;
\q
EOF

# Crear archivo .env para producción
log_info "Configurando variables de entorno..."
cat > .env << 'EOF'
SECRET_KEY=django-production-key-52.20.22.173-change-in-real-production
DEBUG=False
DATABASE_URL=postgresql://admin:admin123@localhost:5432/academic_saas_dev
ALLOWED_HOSTS=localhost,127.0.0.1,52.20.22.173
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000,http://52.20.22.173,http://52.20.22.173:3000
CORS_ALLOW_CREDENTIALS=True
CORS_ALLOW_ALL_ORIGINS=False
EOF

# Ejecutar migraciones con Poetry
log_info "Ejecutando migraciones de base de datos..."
poetry run python manage.py migrate

# Crear superusuario si no existe
log_info "Verificando superusuario..."
poetry run python manage.py shell << 'EOF'
from apps.users.models import User
from apps.organizations.models import School

if not User.objects.filter(username='admin').exists():
    # Crear escuela demo si no existe
    school, created = School.objects.get_or_create(name='Demo School')
    if created:
        print("Escuela demo creada")
    
    # Crear superusuario
    User.objects.create_superuser('admin', 'admin@example.com', 'admin123', school=school)
    print("Superusuario creado: admin / admin123")
else:
    print("Superusuario ya existe: admin / admin123")
EOF

# Recopilar archivos estáticos
log_info "Recopilando archivos estáticos..."
poetry run python manage.py collectstatic --noinput

# ================================================================
# DEPLOYMENT CON SYSTEMD
# ================================================================

log_info "🔄 Configurando servicio systemd..."

# Detener servicio existente si existe
sudo systemctl stop academic-saas-backend 2>/dev/null || log_info "No hay servicio previo ejecutándose"

# Crear servicio systemd
sudo tee /etc/systemd/system/academic-saas-backend.service > /dev/null << EOF
[Unit]
Description=Academic SaaS Backend
After=network.target

[Service]
Type=simple
User=ec2-user
WorkingDirectory=/home/ec2-user/academic-saas-backend
ExecStart=/home/ec2-user/academic-saas-backend/.venv/bin/gunicorn --bind 0.0.0.0:8000 --workers 2 core.wsgi:application
Restart=always
RestartSec=10
EnvironmentFile=/home/ec2-user/academic-saas-backend/.env

[Install]
WantedBy=multi-user.target
EOF

# Recargar systemd y habilitar servicio
sudo systemctl daemon-reload
sudo systemctl enable academic-saas-backend.service

# Crear directorio de logs si no existe
mkdir -p /home/ec2-user/logs

# Iniciar servicio
log_info "🚀 Iniciando servicio backend..."
sudo systemctl start academic-saas-backend

# ================================================================
# INICIAR NGINX
# ================================================================

log_info "🌐 Iniciando nginx..."
sudo systemctl restart nginx

# Verificar que nginx esté funcionando
if sudo systemctl is-active --quiet nginx; then
    log_success "✅ Nginx iniciado correctamente"
else
    log_error "❌ Error: Nginx no pudo iniciarse"
    sudo systemctl status nginx
    exit 1
fi

# ================================================================
# VERIFICACIÓN
# ================================================================

log_info "⏳ Esperando que la aplicación esté lista..."
sleep 10

# Verificar que la aplicación responda directamente (puerto 8000)
if curl -f http://localhost:8000/admin/login/ > /dev/null 2>&1; then
    log_success "✅ Backend responde en puerto 8000"
else
    log_error "❌ Error: Backend no responde en puerto 8000"
    sudo systemctl status academic-saas-backend
    exit 1
fi

# Verificar que nginx proxy funcione (puerto 80)
if curl -f http://localhost/admin/login/ > /dev/null 2>&1; then
    log_success "✅ Nginx proxy funcionando correctamente"
    log_info "🌐 Acceso principal: http://52.20.22.173"
    log_info "🔧 Admin: http://52.20.22.173/admin"
    log_info "🔧 Backend directo: http://52.20.22.173:8000"
else
    log_warning "⚠️ Nginx proxy no responde, pero backend funciona directamente"
    log_info "🌐 URL directa: http://52.20.22.173:8000"
    log_info "🔧 Admin: http://52.20.22.173:8000/admin"
fi

# ================================================================
# INFORMACIÓN FINAL
# ================================================================

log_success "🎉 ¡Deployment completado!"
log_info "======================================"
log_info "🌐 URLs de acceso (Nginx Proxy):"
log_info "   • Aplicación:    http://52.20.22.173"
log_info "   • Backend API:   http://52.20.22.173/api/"
log_info "   • Django Admin:  http://52.20.22.173/admin/"
log_info ""
log_info "🔧 URLs directas (desarrollo):"
log_info "   • Backend:       http://52.20.22.173:8000"
log_info "   • API Docs:      http://52.20.22.173:8000/api/docs/"
log_info ""
log_info "🔑 Credenciales:"
log_info "   • Usuario:       admin"
log_info "   • Contraseña:    admin123"
log_info ""
log_info "📋 Comandos útiles:"
log_info "   • sudo systemctl status academic-saas-backend   # Estado backend"
log_info "   • sudo systemctl status nginx                   # Estado nginx"
log_info "   • sudo systemctl restart academic-saas-backend  # Reiniciar backend"
log_info "   • sudo systemctl restart nginx                  # Reiniciar nginx"
log_info "   • sudo nginx -t                                 # Validar config nginx"
log_info "   • ./deploy_dev.sh --force-deps # Reinstalar dependencias"