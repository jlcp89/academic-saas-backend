# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Full Stack Local Development (Recommended)
```bash
# From project root directory (contains both academic_saas/ and academic-saas-frontend/)
./run_local.sh
```

This script automatically:
- Sets up both backend and frontend environments
- Creates virtual environment and installs dependencies
- Configures environment variables
- Runs database migrations
- Creates superuser (admin/admin123)
- Starts both servers in parallel

**Access URLs:**
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- Django Admin: http://localhost:8000/admin/
- API Docs: http://localhost:8000/api/docs/

### Backend Only Setup
```bash
# Navigate to backend directory
cd academic_saas

# Activate virtual environment
source academic_saas_env/bin/activate

# Install dependencies
pip install -r requirements.txt

# Quick start with automated setup
./run_app.sh

# Manual start
python manage.py runserver 0.0.0.0:8000
```

### Database Management
```bash
# Create migrations after model changes
python manage.py makemigrations

# Apply migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser
```

### Testing
```bash
# Run all tests
python manage.py test

# Run tests for specific app
python manage.py test apps.users
```

### Django Shell
```bash
# Access Django shell for debugging/data manipulation
python manage.py shell
```

## Architecture Overview

### Multi-Tenant SaaS Structure
This is a Django REST Framework-based multi-tenant academic management system where each school operates as an isolated tenant.

### Core Components

**Organizations App** (`apps/organizations/`):
- `School` model: Tenant entities representing academic institutions
- `Subscription` model: Manages billing plans (Basic/Premium) and subscription status
- Each school operates in complete data isolation

**Users App** (`apps/users/`):
- Custom User model extending AbstractUser with role-based access
- Four roles: SUPERADMIN, ADMIN (school admin), PROFESSOR, STUDENT
- All users (except SUPERADMIN) belong to a specific school

**Academic App** (`apps/academic/`):
- Academic entities: subjects, sections, enrollments, assignments, submissions
- All academic data is school-scoped for tenant isolation

### Key Architectural Patterns

**Tenant Isolation** (`apps/base.py`):
- `TenantAwareViewSet`: Base viewset that automatically filters data by user's school
- Ensures complete data isolation between schools
- Auto-assigns school on object creation

**Permission System** (`apps/permissions.py`):
- Role-based permissions: `IsSuperAdmin`, `IsSchoolAdmin`, `IsProfessor`, `IsStudent`
- Object-level permissions: `IsOwnerOrAdmin`, `IsSameSchool`
- Hierarchical access control within tenant boundaries

**Authentication**:
- JWT-based authentication using SimpleJWT
- 60-minute access tokens, 7-day refresh tokens with rotation
- Bearer token authentication in API headers

### Important Development Notes

**Multi-Tenant Data Access**:
- ALWAYS extend `TenantAwareViewSet` for school-scoped models
- Use role-based permissions from `apps/permissions.py`
- Never access cross-school data (except for SUPERADMIN operations)

**Custom User Model**:
- AUTH_USER_MODEL is set to 'users.User'
- User model includes `role` and `school` fields
- SUPERADMIN users have school=None

**API Structure**:
- All endpoints require authentication except login/refresh
- Automatic pagination (20 items per page)
- API documentation available at `/api/docs/` (Swagger) and `/api/redoc/`
- Schema available at `/api/schema/`

**Environment Configuration**:
- Uses python-decouple for environment variables
- Database URL configurable via DATABASE_URL
- Supports both SQLite (dev) and PostgreSQL (production)
- Optional AWS S3 storage for media files

### Default Credentials
- Admin user: `admin` / `admin123`
- Admin panel: http://localhost:8000/admin/

### Current Deployment Status
**Development Environment (Active):**
- Frontend: http://107.21.145.151:3000
- Backend API: http://107.21.145.151:8000
- Django Admin: http://107.21.145.151:8000/admin/
- API Docs: http://107.21.145.151:8000/api/docs/
- Credentials: `admin / admin123`

### Static and Media Files
- Static files served via WhiteNoise in production
- Media files stored locally in `media/` directory
- Optional S3 integration available via environment variables

## Frontend Application

### Technology Stack
- **Framework**: Next.js 15.4.1 with App Router
- **Language**: TypeScript with strict typing
- **Styling**: Tailwind CSS v4
- **State Management**: 
  - React Query (TanStack Query) for server state
  - Zustand for client-side global state
- **Authentication**: NextAuth.js with JWT strategy
- **Forms**: React Hook Form + Zod validation
- **UI Components**: Shadcn/ui (copy-paste component library)

### Frontend Development Commands

```bash
# Navigate to frontend directory
cd academic-saas-frontend

# Install dependencies
npm install

# Run development server
npm run dev

# Build for production
npm run build

# Run production server
npm start

# Lint code
npm run lint

# Type checking
npx tsc --noEmit
```

### Frontend Project Structure

```
academic-saas-frontend/
├── src/
│   ├── app/                    # Next.js App Router pages
│   │   ├── auth/login/         # Authentication pages
│   │   ├── dashboard/          # Main dashboard
│   │   ├── api/auth/           # NextAuth.js API routes
│   │   ├── layout.tsx          # Root layout with providers
│   │   └── page.tsx            # Landing page
│   ├── components/             # Reusable UI components
│   │   └── ui/                 # Shadcn/ui components
│   ├── lib/                    # Utilities and configuration
│   │   ├── api-client.ts       # Authenticated API client
│   │   ├── constants.ts        # API endpoints and constants
│   │   ├── providers.tsx       # React Query + NextAuth providers
│   │   ├── queries.ts          # React Query hooks
│   │   ├── store.ts            # Zustand global state
│   │   └── utils.ts            # General utilities
│   └── types/                  # TypeScript type definitions
│       ├── index.ts            # Main types matching Django models
│       └── next-auth.d.ts      # NextAuth type extensions
```

### Frontend Authentication Flow

1. **Login Process**:
   - User submits credentials via React Hook Form
   - NextAuth.js calls Django `/api/auth/login/` for JWT tokens
   - Gets user data from `/api/users/me/` using access token
   - Stores session with NextAuth.js (secure HTTP-only cookies)

2. **API Requests**:
   - Use `useApiClient()` hook for authenticated requests
   - Automatically includes Bearer token in Authorization header
   - React Query handles caching, background updates, and error states

3. **State Management**:
   - **Server State**: Managed by React Query (user data, schools, subjects, etc.)
   - **UI State**: Managed by Zustand (sidebar open/closed, theme, etc.)
   - **Authentication State**: Managed by NextAuth.js session

### Key Frontend Patterns

**API Integration**:
- Use React Query hooks from `src/lib/queries.ts`
- All API calls are typed with TypeScript interfaces
- Automatic tenant filtering handled by Django backend

**Component Development**:
- Use Shadcn/ui components for consistent UI
- Extend with custom components in `src/components/`
- Follow Next.js App Router conventions

**Form Handling**:
- Use React Hook Form with Zod validation
- Form schemas defined alongside components
- Automatic error handling and validation messages

**Type Safety**:
- All Django models have corresponding TypeScript types
- API responses are fully typed
- Use strict TypeScript configuration

### Environment Configuration

Frontend environment variables (`.env.local`):
```bash
# NextAuth Configuration
NEXTAUTH_URL=http://localhost:3000
NEXTAUTH_SECRET=your-secret-key-change-in-production

# API Configuration  
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### Development Workflow

**Option 1: Automated Full Stack (Recommended)**
```bash
# From project root directory
./run_local.sh
```

**Option 2: Manual Setup**
1. **Start Both Servers**:
   ```bash
   # Terminal 1: Backend (Django)
   cd academic_saas
   ./run_app.sh

   # Terminal 2: Frontend (Next.js)
   cd academic-saas-frontend
   npm run dev
   ```

2. **Access Points**:
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - Django Admin: http://localhost:8000/admin/
   - API Docs: http://localhost:8000/api/docs/

3. **Default Login**: `admin / admin123`

### Frontend API Endpoints Integration

All Django API endpoints are integrated with typed React Query hooks:
- **Authentication**: Login/logout with session management
- **Users**: CRUD operations with role-based access
- **Schools**: Superadmin management (multi-tenant)
- **Academic**: Subjects, sections, assignments, submissions
- **Enrollments**: Student course enrollment management

### Deployment Notes

- Frontend builds to static files with `npm run build`
- Can be deployed to Vercel, Netlify, or any static hosting
- Requires environment variables for production API URL
- NextAuth.js requires secure session configuration for production

## AWS Infrastructure Implementation

### Overview
La infraestructura de Academic SaaS está implementada en AWS con un enfoque de costos mínimos para desarrollo y capacidad de escalar a producción. Se utiliza una arquitectura modular con Terraform para gestionar la infraestructura como código.

### Arquitectura de Desarrollo (Actual)

#### 1. **Instancia EC2 Única (Modo Desarrollo)**
- **Tipo**: t2.micro (Free tier eligible)
- **AMI**: Amazon Linux 2
- **IP Pública**: 107.21.145.151
- **Servicios**: Todos los servicios ejecutándose en Docker
  - PostgreSQL 15 (puerto 5432)
  - Redis 7 (puerto 6379)
  - Django Backend (puerto 8000)
  - Next.js Frontend (puerto 3000)

#### 2. **Networking**
- **VPC**: 10.0.0.0/16
- **Subnets**: 
  - 3 subnets públicas (us-east-1a, us-east-1b, us-east-1c)
  - 3 subnets privadas
- **Security Group**: academic-saas-dev-minimal
  - SSH (22): 0.0.0.0/0
  - HTTP Backend (8000): 0.0.0.0/0
  - HTTP Frontend (3000): 0.0.0.0/0
  - PostgreSQL (5432): VPC CIDR
  - Redis (6379): VPC CIDR

#### 3. **Almacenamiento**
- **S3 Bucket**: academic-saas-dev-7244fcb3
  - Para archivos estáticos y media
  - Configurado con políticas de acceso para EC2
- **EBS**: 8GB GP2 (Free tier)

#### 4. **Container Registry**
- **ECR Repositories**:
  - `academic-saas-backend`: Imágenes del backend Django
  - `academic-saas-frontend`: Imágenes del frontend Next.js

### Arquitectura de Producción (Preparada)

#### 1. **Auto Scaling Groups**
- **Backend ASG**:
  - Min: 2, Max: 10, Desired: 3
  - Instance type: t3.medium
  - Health checks via ALB
  - Rolling deployment strategy
- **Frontend ASG**:
  - Min: 2, Max: 8, Desired: 2
  - Instance type: t3.small

#### 2. **Load Balancers**
- **Backend ALB**: 
  - DNS: academic-saas-dev-backend-alb-*.elb.amazonaws.com
  - Target Group: Puerto 8000
  - Health check: /admin/login/
- **Frontend ALB**:
  - DNS: academic-saas-dev-frontend-alb-*.elb.amazonaws.com
  - Target Group: Puerto 3000
  - Health check: /

#### 3. **Base de Datos (Opciones)**
- **RDS PostgreSQL** (preparado pero no activo):
  - Multi-AZ para alta disponibilidad
  - Automated backups
  - Read replicas para escalar lecturas
- **PostgreSQL en Docker** (actual):
  - Más económico para desarrollo
  - Datos persistentes en volúmenes Docker

#### 4. **Cache**
- **ElastiCache Redis** (preparado pero no activo):
  - Cluster mode con 3 nodos
  - Automatic failover
- **Redis en Docker** (actual):
  - Single node para desarrollo

### Configuración de Terraform

#### Archivos Principales:
1. **`variables.tf`**: Define todas las variables configurables
2. **`main.tf`**: VPC, subnets, security groups
3. **`autoscaling.tf`**: Launch templates y ASGs
4. **`elastic-ips.tf`**: ALBs y target groups
5. **`dev-minimal.tf`**: Configuración de desarrollo con instancia única
6. **`s3.tf`**: Bucket para archivos estáticos
7. **`iam.tf`**: Roles y políticas IAM
8. **`ecr.tf`**: Repositorios de contenedores

#### Variables de Entorno:
```hcl
# Modo desarrollo (costos mínimos)
dev_minimal_mode = true

# Configuración por entorno
environment_config = {
  dev = {
    backend_instance_type = "t2.micro"
    frontend_instance_type = "t2.micro"
    backend_min_size = 1
    backend_max_size = 1
  }
  prod = {
    backend_instance_type = "t3.medium"
    frontend_instance_type = "t3.small"
    backend_min_size = 2
    backend_max_size = 10
  }
}
```

### CI/CD Pipeline

#### GitHub Actions Workflows:
1. **Backend Deploy** (`.github/workflows/backend-deploy.yml`):
   - Trigger: Push a main o manual
   - Build Docker image
   - Push a ECR
   - Deploy a instancias EC2 via SSH

2. **Frontend Deploy** (similar proceso)

#### Secretos Configurados:
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `AWS_REGION`
- `EC2_SSH_PRIVATE_KEY`

### Scripts de Despliegue

#### 1. **User Data Scripts**:
- `user-data-dev-minimal.sh`: Configura la instancia de desarrollo
- `user-data-backend-amazonlinux.sh`: Para instancias de producción
- Instalan Docker, crean contenedores, configuran servicios

#### 2. **Deployment Script** (`deploy-full-stack.sh`):
```bash
# Despliega backend o frontend desde ECR
./deploy-full-stack.sh <ECR_REGISTRY> <BACKEND_IMAGE> <FRONTEND_IMAGE> <backend|frontend|all>
```

### Gestión de Costos

#### Desarrollo (Actual):
- **EC2**: $0 (t2.micro free tier)
- **Storage**: $0 (dentro de free tier)
- **Network**: ~$0.01/GB transferencia
- **Total**: < $1/mes

#### Producción (Estimado):
- **EC2 (5 instancias)**: ~$150/mes
- **ALB (2)**: ~$35/mes
- **RDS**: ~$50/mes
- **ElastiCache**: ~$25/mes
- **Total**: ~$260/mes base

### Comandos de Gestión

#### Terraform:
```bash
# Inicializar
terraform init

# Plan de desarrollo
terraform plan -var-file=dev.tfvars

# Aplicar cambios
terraform apply -var-file=dev.tfvars

# Cambiar a producción
terraform apply -var-file=prod.tfvars
```

#### AWS CLI:
```bash
# Ver instancias
aws ec2 describe-instances --filters "Name=tag:Environment,Values=dev"

# Escalar ASG
aws autoscaling set-desired-capacity --auto-scaling-group-name academic-saas-dev-backend-asg --desired-capacity 3

# Ver logs de contenedor
ssh -i ~/.ssh/academic_saas_aws ec2-user@<IP> "docker logs academic-saas-backend"
```

### Monitoreo y Alertas

#### CloudWatch Metrics:
- CPU utilization
- Memory usage
- Request count
- Error rates

#### Alarms Configuradas:
- High CPU (>70%)
- Low CPU (<20%)
- Unhealthy targets
- Failed deployments

### Seguridad

#### IAM Roles:
- **EC2 Instance Role**: Acceso a S3, ECR, CloudWatch
- **GitHub Actions Role**: Deploy permissions

#### Network Security:
- Security groups restrictivos
- Subnets privadas para backend en producción
- HTTPS con certificados SSL (preparado)

### Backup y Recuperación

#### Estrategias:
1. **Database**: 
   - Snapshots diarios de volúmenes Docker
   - RDS automated backups (producción)
2. **Aplicaciones**:
   - Imágenes versionadas en ECR
   - Rollback capability via ASG
3. **Configuración**:
   - Terraform state en S3 con versioning
   - Secretos en AWS Secrets Manager

### URLs de Acceso

#### Desarrollo:
- Frontend: http://107.21.145.151:3000
- Backend API: http://107.21.145.151:8000
- Django Admin: http://107.21.145.151:8000/admin/
- API Docs: http://107.21.145.151:8000/api/docs/

#### Producción (cuando se active):
- Frontend: https://app.yourdomain.com
- Backend API: https://api.yourdomain.com
- Con SSL/TLS y dominio personalizado

## Despliegue y Operaciones

### Estado Actual del Despliegue

**Entorno de Desarrollo Activo:**
- **IP Pública**: 107.21.145.151
- **Instancia EC2**: i-0c6e4d284dfcfe05d (t2.micro)
- **Estado**: Completamente funcional
- **Containers Docker Activos**:
  - PostgreSQL (puerto 5432)
  - Redis (puerto 6379)
  - Django Backend (puerto 8000)
  - Next.js Frontend (puerto 3000)

### Acceso a la Aplicación

**URLs de Acceso:**
- **Frontend**: http://107.21.145.151:3000
- **Login**: http://107.21.145.151:3000/auth/login
- **Backend API**: http://107.21.145.151:8000
- **Django Admin**: http://107.21.145.151:8000/admin/
- **API Docs**: http://107.21.145.151:8000/api/docs/

**Credenciales de Acceso:**
- **Usuario**: admin
- **Contraseña**: admin123

### Comandos de Mantenimiento

#### Acceso SSH a la Instancia:
```bash
ssh -i ~/.ssh/academic_saas_aws ec2-user@107.21.145.151
```

#### Gestión de Contenedores:
```bash
# Ver estado de contenedores
docker ps

# Ver logs de backend
docker logs academic-saas-backend

# Ver logs de frontend
docker logs academic-saas-frontend

# Reiniciar servicios
docker restart academic-saas-backend
docker restart academic-saas-frontend

# Acceder a la base de datos
docker exec -it postgres psql -U academic_user -d academic_saas_dev
```

#### Administración de Django:
```bash
# Ejecutar comandos Django en el contenedor
docker exec academic-saas-backend python manage.py <comando>

# Crear nuevo superusuario
docker exec -it academic-saas-backend python manage.py createsuperuser

# Ejecutar migraciones
docker exec academic-saas-backend python manage.py migrate

# Acceder al shell de Django
docker exec -it academic-saas-backend python manage.py shell
```

### Solución de Problemas Comunes

#### 1. **Frontend no se actualiza con cambios del backend**
**Problema**: Los datos del usuario no se actualizan automáticamente en el frontend.
**Causa**: NextAuth.js almacena datos en JWT sin refrescar automáticamente.
**Soluciones**:
- Cerrar sesión y volver a iniciar (más simple)
- Usar el hook `useCurrentUser()` en el código del frontend
- Forzar actualización con `window.location.reload()` desde la consola

#### 2. **Contenedores no se comunican**
**Problema**: Error de conexión entre servicios.
**Solución**: Verificar que todos los contenedores estén en la misma red Docker:
```bash
docker network ls
docker network inspect academic-saas-network
```

#### 3. **Permisos de Docker**
**Problema**: Error de permisos al ejecutar comandos Docker.
**Solución**: Usar `sudo` o agregar usuario al grupo docker:
```bash
sudo usermod -aG docker ec2-user
```

#### 4. **Errores de CORS en el frontend**
**Problema**: Errores de CORS al conectar frontend con backend.
**Solución**: Verificar variables de entorno del frontend:
```bash
# Variables requeridas
NEXT_PUBLIC_API_URL=http://107.21.145.151:8000
NEXTAUTH_URL=http://107.21.145.151:3000
```

### Configuración de Entorno

#### Variables de Entorno del Backend:
```bash
SECRET_KEY=django-insecure-temp-key-for-development-only-12345
DEBUG=True
DATABASE_URL=postgresql://academic_user:supersecret123@postgres:5432/academic_saas_dev
REDIS_URL=redis://redis:6379/0
ALLOWED_HOSTS=*
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://107.21.145.151:3000
```

#### Variables de Entorno del Frontend:
```bash
NEXT_PUBLIC_API_URL=http://107.21.145.151:8000
NEXTAUTH_URL=http://107.21.145.151:3000
NEXTAUTH_SECRET=dev-secret-key-change-in-production
```

### Actualización de Código

#### Rebuild del Frontend:
```bash
# En la instancia EC2
cd /tmp/frontend-updated
docker build -t academic-saas-frontend:latest .
docker stop academic-saas-frontend
docker rm academic-saas-frontend
docker run -d --name academic-saas-frontend --restart unless-stopped --network host -e NEXT_PUBLIC_API_URL=http://107.21.145.151:8000 -e NEXTAUTH_URL=http://107.21.145.151:3000 -e NEXTAUTH_SECRET=dev-secret-key-change-in-production academic-saas-frontend:latest
```

#### Deployment desde ECR:
```bash
# Login a ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 860639121390.dkr.ecr.us-east-1.amazonaws.com

# Deploy backend
./deploy-full-stack.sh 860639121390.dkr.ecr.us-east-1.amazonaws.com 860639121390.dkr.ecr.us-east-1.amazonaws.com/academic-saas-backend:latest 860639121390.dkr.ecr.us-east-1.amazonaws.com/academic-saas-frontend:latest backend
```

### Monitoreo y Logs

#### Verificar Estado del Sistema:
```bash
# Script de estado personalizado
./check-status.sh

# Verificar salud de servicios
curl -I http://107.21.145.151:8000/admin/login/  # Backend
curl -I http://107.21.145.151:3000/              # Frontend
```

#### Logs y Debugging:
```bash
# Logs de containers
docker logs academic-saas-backend --tail 100
docker logs academic-saas-frontend --tail 100

# Logs del sistema
sudo journalctl -u docker

# Verificar uso de recursos
docker stats
```

### Gestión de Costos

#### Comandos para Minimizar Costos:
```bash
# Detener instancias no utilizadas
aws ec2 stop-instances --instance-ids i-0c6e4d284dfcfe05d

# Verificar ASG en 0 para evitar costos
aws autoscaling describe-auto-scaling-groups --query "AutoScalingGroups[*].{Name:AutoScalingGroupName,Min:MinSize,Max:MaxSize,Desired:DesiredCapacity}"

# Eliminar recursos no utilizados
aws ec2 describe-addresses --query "Addresses[?InstanceId==null]"
```

### Información de Contacto y Configuración

#### Archivos de Configuración Críticos:
- **SSH Key**: `/home/jl/.ssh/academic_saas_aws`
- **AWS Credentials**: `/home/jl/.aws/credentials`
- **Docker Network**: `academic-saas-network`
- **ECR Registry**: `860639121390.dkr.ecr.us-east-1.amazonaws.com`

#### Repositorios:
- **Backend**: https://github.com/joralroma/academic-saas-backend
- **Frontend**: https://github.com/joralroma/academic-saas-frontend

#### Modelos de Datos Importantes:
- **User**: username, email, role, school, is_active
- **School**: name, subdomain, is_active
- **Subscription**: school, plan, start_date, end_date, is_active

### Notas para Futuras Sesiones

1. **Siempre verificar estado de contenedores** antes de hacer cambios
2. **Usar docker logs** para debugging antes de reiniciar servicios
3. **Mantener ASG en 0** para evitar costos innecesarios
4. **Validar conectividad de red** entre contenedores Docker
5. **Actualizar datos del usuario** requiere logout/login o refresh manual
6. **Usar variables de entorno correctas** para comunicación entre servicios
7. **Verificar security groups** si hay problemas de conectividad
8. **Mantener backups** de datos críticos antes de cambios importantes

### Common Development Issues

1. **Frontend data not updating**: NextAuth.js caches user data in JWT tokens. Solution: logout/login or force refresh
2. **CORS errors**: Verify CORS_ALLOWED_ORIGINS in Django settings includes frontend URL
3. **Database connection issues**: Check DATABASE_URL environment variable
4. **Authentication failures**: Verify NEXT_PUBLIC_API_URL points to correct backend

### Project Scripts Reference

- `./run_local.sh`: Full stack local development (root directory)
- `./run_app.sh`: Backend only (academic_saas directory)
- `./deploy-full-stack.sh`: Production deployment script
- `./verificar-infraestructura.sh`: Infrastructure verification

### Repository Structure

```
project-root/
├── academic_saas/           # Django backend repository
├── academic-saas-frontend/  # Next.js frontend repository
├── run_local.sh            # Full stack development script
└── *.sh                    # Various deployment/setup scripts
```

### Git Repositories

- **Backend**: https://github.com/jlcp89/academic-saas-backend
- **Frontend**: https://github.com/jlcp89/academic-saas-frontend

### Próximos Pasos Recomendados

1. Implementar sistema de actualizaciones automáticas para datos del usuario
2. Configurar dominio personalizado con SSL/TLS
3. Implementar sistema de backups automatizados
4. Crear ambiente de staging separado
5. Configurar monitoreo y alertas proactivas
6. Implementar CI/CD completo para deployment automático