#!/bin/bash

# Academic SaaS Local Development Setup Script
# Runs both backend and frontend with full stack support
# Includes: ASGI (Daphne), Next.js, Chat, AI system, Nginx proxy

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
BACKEND_DIR="$SCRIPT_DIR"
FRONTEND_DIR="$SCRIPT_DIR/../academic-saas-frontend"

# Configuration
BACKEND_PORT=8000
FRONTEND_PORT=3000
REDIS_HOST="52.20.22.173"
REDIS_PORT=6379
DB_HOST="52.20.22.173"
DB_PORT=5432
DB_NAME="academic_saas_dev"
DB_USER="admin"
DB_PASS="admin123"

echo -e "${CYAN}========================================${NC}"
echo -e "${CYAN}  Academic SaaS Local Development${NC}"
echo -e "${CYAN}========================================${NC}"
echo ""

# Function to print status messages
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check if port is in use
port_in_use() {
    netstat -tuln 2>/dev/null | grep -q ":$1 "
}

# Function to kill process on port
kill_port() {
    local port=$1
    local pids=$(lsof -ti:$port 2>/dev/null)
    if [ ! -z "$pids" ]; then
        print_warning "Killing processes on port $port: $pids"
        kill -9 $pids 2>/dev/null
        sleep 2
    fi
}

# Function to check system requirements
check_requirements() {
    print_status "Checking system requirements..."
    
    # Check Python
    if ! command_exists python3; then
        print_error "Python 3 is required but not installed"
        exit 1
    fi
    
    # Check Node.js
    if ! command_exists node; then
        print_error "Node.js is required but not installed"
        exit 1
    fi
    
    # Check npm
    if ! command_exists npm; then
        print_error "npm is required but not installed"
        exit 1
    fi
    
    # Check pip
    if ! command_exists pip3; then
        print_error "pip3 is required but not installed"
        exit 1
    fi
    
    print_success "All system requirements met"
}

# Function to setup backend environment
setup_backend() {
    print_status "Setting up backend environment..."
    
    cd "$BACKEND_DIR"
    
    # Create virtual environment if it doesn't exist
    if [ ! -d "venv" ]; then
        print_status "Creating Python virtual environment..."
        python3 -m venv venv
    fi
    
    # Activate virtual environment
    print_status "Activating virtual environment..."
    source venv/bin/activate
    
    # Upgrade pip
    print_status "Upgrading pip..."
    pip install --upgrade pip
    
    # Install dependencies
    print_status "Installing Python dependencies..."
    pip install -r requirements.txt
    
    print_success "Backend environment setup complete"
}

# Function to setup frontend environment
setup_frontend() {
    print_status "Setting up frontend environment..."
    
    if [ ! -d "$FRONTEND_DIR" ]; then
        print_error "Frontend directory not found: $FRONTEND_DIR"
        print_error "Please clone the frontend repository to: $FRONTEND_DIR"
        exit 1
    fi
    
    cd "$FRONTEND_DIR"
    
    # Install npm dependencies
    print_status "Installing Node.js dependencies..."
    npm install
    
    print_success "Frontend environment setup complete"
}

# Function to check database connection
check_database() {
    print_status "Checking database connection..."
    
    cd "$BACKEND_DIR"
    source venv/bin/activate
    
    # Test database connection using Django
    python -c "
import os, sys
sys.path.append('.')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
import django
django.setup()
from django.db import connection
try:
    cursor = connection.cursor()
    cursor.execute('SELECT 1')
    print('Database connection: OK')
except Exception as e:
    print(f'Database connection failed: {e}')
    sys.exit(1)
" || {
        print_error "Database connection failed"
        print_error "Please ensure PostgreSQL is running on $DB_HOST:$DB_PORT"
        exit 1
    }
    
    print_success "Database connection verified"
}

# Function to check Redis connection
check_redis() {
    print_status "Checking Redis connection..."
    
    # Test Redis connection
    if command_exists redis-cli; then
        redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" ping >/dev/null 2>&1 || {
            print_warning "Redis connection failed - Chat notifications may not work"
            print_warning "Redis server should be running on $REDIS_HOST:$REDIS_PORT"
            return 1
        }
        print_success "Redis connection verified"
    else
        print_warning "redis-cli not installed - skipping Redis check"
        print_warning "Install redis-tools: sudo apt-get install redis-tools"
    fi
}

# Function to setup environment variables
setup_environment() {
    print_status "Setting up environment variables..."
    
    cd "$BACKEND_DIR"
    
    # Create .env file if it doesn't exist
    if [ ! -f ".env" ]; then
        print_status "Creating backend .env file..."
        cat > .env << EOF
SECRET_KEY=django-insecure-academic-saas-development-key-2024
DEBUG=True
DATABASE_URL=postgresql://$DB_USER:$DB_PASS@$DB_HOST:$DB_PORT/$DB_NAME
ALLOWED_HOSTS=localhost,127.0.0.1,*
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
CORS_ALLOW_CREDENTIALS=True
DISABLE_MIGRATION_CHECK=True
REDIS_HOST=$REDIS_HOST
REDIS_PORT=$REDIS_PORT
CELERY_BROKER_URL=redis://$REDIS_HOST:$REDIS_PORT/0
CELERY_RESULT_BACKEND=redis://$REDIS_HOST:$REDIS_PORT/0
EOF
    fi
    
    # Setup frontend environment
    cd "$FRONTEND_DIR"
    if [ ! -f ".env.local" ]; then
        print_status "Creating frontend .env.local file..."
        cat > .env.local << EOF
# Dynamic environment detection is enabled in lib/constants.ts
# These variables are fallbacks for SSR/build time
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXTAUTH_URL=http://localhost:3000
NEXTAUTH_SECRET=/bG5bl9y23JSqYstIc/c+uoY/3eIwlPeInJU9kiJd7I=
NODE_ENV=development

# Ensure API connects to backend server
NEXT_PUBLIC_BACKEND_URL=http://localhost:8000
EOF
    fi
    
    print_success "Environment variables configured"
}

# Function to setup AI system
setup_ai_system() {
    print_status "Setting up AI system..."
    
    cd "$BACKEND_DIR"
    source venv/bin/activate
    
    # Install AI dependencies
    print_status "Installing AI dependencies..."
    pip install scikit-learn joblib pandas numpy matplotlib seaborn
    
    # Train model if it doesn't exist
    if [ ! -f "models/academic_risk_model.pkl" ]; then
        print_status "Training initial AI model..."
        mkdir -p models
        python manage.py train_risk_model || print_warning "AI model training failed"
    fi
    
    # Generate test data
    print_status "Generating test data..."
    python manage.py shell << 'EOF' || print_warning "Test data generation failed"
from apps.users.models import User
from apps.organizations.models import School
from apps.academic.models import Subject, Section, Assignment, Submission
from apps.ai.management.commands.train_risk_model import create_sample_data
import os

# Only create test data if minimal data exists
if User.objects.count() < 5:
    print("Creating test data for AI system...")
    create_sample_data()
    print("Test data created successfully")
else:
    print("Test data already exists")
EOF
    
    print_success "AI system setup complete"
}

# Function to check nginx and ask user preference
setup_nginx() {
    print_status "Checking Nginx configuration..."
    
    if command_exists nginx; then
        echo ""
        echo -e "${YELLOW}¿Quieres usar Nginx para proxy local? (recomendado para CSS/estilos) [y/N]:${NC}"
        read -r use_nginx
        
        if [[ $use_nginx =~ ^[Yy]$ ]]; then
            print_status "Configurando Nginx proxy local..."
            
            # Backup current nginx config
            if [ -f "/etc/nginx/nginx.conf" ]; then
                sudo cp /etc/nginx/nginx.conf /etc/nginx/nginx.conf.backup.$(date +%Y%m%d_%H%M%S) 2>/dev/null || true
            fi
            
            # Copy local nginx config
            if [ -f "$BACKEND_DIR/nginx-local.conf" ]; then
                sudo cp "$BACKEND_DIR/nginx-local.conf" /etc/nginx/nginx.conf
                
                # Test nginx config
                if sudo nginx -t 2>/dev/null; then
                    sudo systemctl reload nginx || sudo service nginx reload
                    print_success "Nginx configurado correctamente"
                    echo ""
                    echo -e "${GREEN}Acceso mediante Nginx proxy:${NC}"
                    echo -e "  Frontend: ${CYAN}http://localhost/${NC}"
                    echo -e "  Backend:  ${CYAN}http://localhost/api/${NC}"
                    echo -e "  Admin:    ${CYAN}http://localhost/admin/${NC}"
                    echo ""
                    USE_NGINX=true
                else
                    print_error "Error en configuración de Nginx"
                    USE_NGINX=false
                fi
            else
                print_warning "Archivo nginx-local.conf no encontrado"
                USE_NGINX=false
            fi
        else
            USE_NGINX=false
        fi
    else
        print_warning "Nginx no está instalado - usando acceso directo"
        USE_NGINX=false
    fi
}

# Function to start backend
start_backend() {
    print_status "Starting backend server..."
    
    cd "$BACKEND_DIR"
    source venv/bin/activate
    
    # Kill any existing processes
    kill_port $BACKEND_PORT
    
    # Collect static files
    print_status "Collecting static files..."
    python manage.py collectstatic --noinput --clear >/dev/null 2>&1
    
    # Start backend with Daphne for WebSocket support
    print_status "Starting Daphne ASGI server on port $BACKEND_PORT..."
    echo ""
    echo -e "${GREEN}Backend starting...${NC}"
    echo -e "  API: ${CYAN}http://localhost:$BACKEND_PORT/api/${NC}"
    echo -e "  Admin: ${CYAN}http://localhost:$BACKEND_PORT/admin/${NC}"
    echo -e "  Docs: ${CYAN}http://localhost:$BACKEND_PORT/api/docs/${NC}"
    echo ""
    
    # Start Daphne in background
    nohup daphne -b 0.0.0.0 -p $BACKEND_PORT core.asgi:application > backend.log 2>&1 &
    BACKEND_PID=$!
    
    # Wait for backend to start
    sleep 3
    
    # Check if backend started successfully
    if port_in_use $BACKEND_PORT; then
        print_success "Backend server started successfully (PID: $BACKEND_PID)"
    else
        print_error "Backend server failed to start"
        print_error "Check backend.log for details"
        exit 1
    fi
}

# Function to start frontend
start_frontend() {
    print_status "Starting frontend server..."
    
    cd "$FRONTEND_DIR"
    
    # Kill any existing processes
    kill_port $FRONTEND_PORT
    
    # Build frontend if needed
    if [ ! -d ".next" ]; then
        print_status "Building frontend..."
        npm run build
    fi
    
    print_status "Starting Next.js development server on port $FRONTEND_PORT..."
    echo ""
    echo -e "${GREEN}Frontend starting...${NC}"
    echo -e "  App: ${CYAN}http://localhost:$FRONTEND_PORT/${NC}"
    echo -e "  Chat: ${CYAN}http://localhost:$FRONTEND_PORT/chat${NC}"
    echo ""
    
    # Start frontend in background
    nohup npm run dev > ../academic_saas/frontend.log 2>&1 &
    FRONTEND_PID=$!
    
    # Wait for frontend to start
    sleep 5
    
    # Check if frontend started successfully
    if port_in_use $FRONTEND_PORT; then
        print_success "Frontend server started successfully (PID: $FRONTEND_PID)"
    else
        print_error "Frontend server failed to start"
        print_error "Check frontend.log for details"
        exit 1
    fi
}

# Function to show final status
show_status() {
    echo ""
    echo -e "${CYAN}========================================${NC}"
    echo -e "${CYAN}     Development Environment Ready${NC}"
    echo -e "${CYAN}========================================${NC}"
    echo ""
    
    if [ "$USE_NGINX" = true ]; then
        echo -e "${GREEN}🚀 Access via Nginx Proxy (Recommended):${NC}"
        echo -e "   Frontend:    ${CYAN}http://localhost/${NC}"
        echo -e "   Backend API: ${CYAN}http://localhost/api/${NC}"
        echo -e "   Django Admin:${CYAN}http://localhost/admin/${NC}"
        echo -e "   Chat:        ${CYAN}http://localhost/chat${NC}"
        echo ""
    fi
    
    echo -e "${GREEN}🔗 Direct Access:${NC}"
    echo -e "   Frontend:    ${CYAN}http://localhost:$FRONTEND_PORT/${NC}"
    echo -e "   Backend API: ${CYAN}http://localhost:$BACKEND_PORT/api/${NC}"
    echo -e "   Django Admin:${CYAN}http://localhost:$BACKEND_PORT/admin/${NC}"
    echo -e "   API Docs:    ${CYAN}http://localhost:$BACKEND_PORT/api/docs/${NC}"
    echo -e "   Chat:        ${CYAN}http://localhost:$FRONTEND_PORT/chat${NC}"
    echo ""
    
    echo -e "${GREEN}🔐 Default Credentials:${NC}"
    echo -e "   Username: ${CYAN}admin${NC}"
    echo -e "   Password: ${CYAN}admin123${NC}"
    echo ""
    
    echo -e "${GREEN}📊 Features Available:${NC}"
    echo -e "   💬 Real-time Chat System with WebSocket"
    echo -e "   🤖 AI Academic Risk Prediction"
    echo -e "   📚 Academic Management (Subjects, Assignments)"
    echo -e "   👥 Multi-tenant User Management"
    echo -e "   📊 Dashboard and Reporting"
    echo ""
    
    echo -e "${GREEN}🔧 Backend Process ID:${NC} $BACKEND_PID"
    echo -e "${GREEN}🔧 Frontend Process ID:${NC} $FRONTEND_PID"
    echo ""
    
    echo -e "${YELLOW}📋 Logs:${NC}"
    echo -e "   Backend:  tail -f $BACKEND_DIR/backend.log"
    echo -e "   Frontend: tail -f $BACKEND_DIR/frontend.log"
    echo ""
    
    echo -e "${YELLOW}🛑 To stop servers:${NC}"
    echo -e "   kill $BACKEND_PID $FRONTEND_PID"
    echo -e "   Or: pkill -f daphne && pkill -f \"next-server\""
    echo ""
    
    echo -e "${GREEN}Ready for development! 🎉${NC}"
}

# Function to cleanup on exit
cleanup() {
    echo ""
    print_status "Shutting down development environment..."
    
    # Kill backend and frontend if PIDs are set
    if [ ! -z "$BACKEND_PID" ]; then
        kill $BACKEND_PID 2>/dev/null || true
    fi
    if [ ! -z "$FRONTEND_PID" ]; then
        kill $FRONTEND_PID 2>/dev/null || true
    fi
    
    # Kill any remaining processes on our ports
    kill_port $BACKEND_PORT
    kill_port $FRONTEND_PORT
    
    print_success "Development environment stopped"
    exit 0
}

# Trap SIGINT and SIGTERM for cleanup
trap cleanup SIGINT SIGTERM

# Main execution
main() {
    # Check requirements
    check_requirements
    
    # Setup environments
    setup_backend
    setup_frontend
    setup_environment
    
    # Check connections
    check_database
    check_redis
    
    # Setup systems
    setup_ai_system
    setup_nginx
    
    # Start servers
    start_backend
    start_frontend
    
    # Show status
    show_status
    
    # Keep script running
    echo -e "${YELLOW}Press Ctrl+C to stop all servers...${NC}"
    echo ""
    
    # Monitor processes
    while true; do
        sleep 10
        
        # Check if backend is still running
        if ! port_in_use $BACKEND_PORT; then
            print_error "Backend server stopped unexpectedly"
            break
        fi
        
        # Check if frontend is still running
        if ! port_in_use $FRONTEND_PORT; then
            print_error "Frontend server stopped unexpectedly"
            break
        fi
    done
    
    cleanup
}

# Run main function
main "$@"