# Academic SaaS Platform

A multi-tenant academic management SaaS application built with Django and Django REST Framework.

## Features

- **Multi-Tenant Architecture**: Each school operates in a securely isolated environment
- **Role-Based Access Control**: Superadmin, School Admin, Professor, and Student roles
- **Academic Management**: Subjects, sections, enrollments, assignments, and submissions
- **Subscription Management**: Basic and Premium plans with expiration tracking
- **JWT Authentication**: Secure token-based authentication
- **RESTful API**: Complete API with documentation
- **Automated Deployment**: GitHub Actions CI/CD pipeline for automated testing and deployment

## Project Structure

```
academic_saas/
├── apps/
│   ├── organizations/    # Manages schools (tenants) and subscriptions
│   ├── users/           # User management with role-based access
│   └── academic/        # Academic features (subjects, sections, etc.)
├── core/                # Main Django project settings
└── manage.py
```

## Local Development

### Quick Start (Full Stack)

If you have both backend and frontend repositories, use the automated script:

```bash
# From the parent directory containing both repos
./run_local.sh
```

This script will:
- Set up both backend and frontend environments
- Install all dependencies
- Configure environment variables
- Run database migrations
- Create superuser automatically
- Start both servers in parallel

**Access URLs:**
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- Django Admin: http://localhost:8000/admin/
- API Docs: http://localhost:8000/api/docs/

**Default Credentials:** `admin / admin123`

### Manual Backend Setup

1. **Create virtual environment**:
   ```bash
   python -m venv academic_saas_env
   source academic_saas_env/bin/activate  # On Windows: academic_saas_env\Scripts\activate
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment variables**:
   Create `.env` file with:
   ```bash
   SECRET_KEY=django-insecure-local-development-key-12345
   DEBUG=True
   DATABASE_URL=sqlite:///db.sqlite3
   ALLOWED_HOSTS=localhost,127.0.0.1
   CORS_ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
   ```

4. **Run migrations**:
   ```bash
   python manage.py migrate
   ```

5. **Create superuser**:
   ```bash
   python manage.py createsuperuser
   ```

6. **Quick start script**:
   ```bash
   ./run_app.sh
   ```

   Or manually:
   ```bash
   python manage.py runserver 0.0.0.0:8000
   ```

## API Endpoints

### Authentication
- `POST /api/auth/login/` - Login with username and password
- `POST /api/auth/refresh/` - Refresh JWT token

### Superadmin Endpoints
- `POST /api/superadmin/schools/` - Create new school
- `GET /api/superadmin/schools/` - List all schools
- `PUT /api/superadmin/subscriptions/{id}/` - Update subscription

### School Admin Endpoints
- `POST /api/users/` - Create users in their school
- `POST /api/subjects/` - Create subjects
- `POST /api/sections/` - Create sections

### Professor Endpoints
- `GET /api/sections/` - View assigned sections
- `POST /api/assignments/` - Create assignments
- `POST /api/submissions/{id}/grade/` - Grade submissions

### Student Endpoints
- `GET /api/enrollments/my_enrollments/` - View enrollments
- `GET /api/assignments/` - View assignments
- `POST /api/submissions/` - Submit assignments

## API Documentation

- Swagger UI: `/api/docs/`
- ReDoc: `/api/redoc/`
- OpenAPI Schema: `/api/schema/`

## Data Isolation

All data is automatically filtered by the user's school using the `TenantAwareViewSet` base class. This ensures complete data isolation between schools.

## Testing

Run tests with:
```bash
python manage.py test
```

## Deployment

### Development Environment (Active)

The development environment is currently deployed and accessible at:

- **Frontend**: http://107.21.145.151:3000
- **Backend API**: http://107.21.145.151:8000
- **Django Admin**: http://107.21.145.151:8000/admin/
- **API Docs**: http://107.21.145.151:8000/api/docs/

**Credentials:** `admin / admin123`

### Deployment Process

#### Automatic Deployment (GitHub Actions)

1. **Push to main branch** triggers automatic deployment
2. **GitHub Actions** builds and pushes Docker images to ECR
3. **EC2 instances** automatically pull and deploy the new images

#### Manual Deployment

```bash
# Deploy backend
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 860639121390.dkr.ecr.us-east-1.amazonaws.com

# Access EC2 instance
ssh -i ~/.ssh/academic_saas_aws ec2-user@107.21.145.151

# Deploy latest backend image
docker pull 860639121390.dkr.ecr.us-east-1.amazonaws.com/academic-saas-backend:latest
docker stop academic-saas-backend || true
docker rm academic-saas-backend || true
docker run -d --name academic-saas-backend --restart unless-stopped --network host -e DATABASE_URL=postgresql://academic_user:supersecret123@postgres:5432/academic_saas_dev -e REDIS_URL=redis://redis:6379/0 -e SECRET_KEY=django-insecure-temp-key-for-development-only-12345 -e DEBUG=True -e ALLOWED_HOSTS=* -e CORS_ALLOWED_ORIGINS=http://localhost:3000,http://107.21.145.151:3000 860639121390.dkr.ecr.us-east-1.amazonaws.com/academic-saas-backend:latest
```

### Infrastructure

**Current Setup:**
- **AWS EC2**: t2.micro instance (107.21.145.151)
- **Docker Containers**: PostgreSQL, Redis, Django, Next.js
- **ECR**: Container registry for images
- **GitHub Actions**: CI/CD pipeline

**Monitoring:**
```bash
# Check container status
docker ps

# View logs
docker logs academic-saas-backend

# Access database
docker exec -it postgres psql -U academic_user -d academic_saas_dev
```

### Environment Variables (Production)

```bash
SECRET_KEY=django-insecure-temp-key-for-development-only-12345
DEBUG=True
DATABASE_URL=postgresql://academic_user:supersecret123@postgres:5432/academic_saas_dev
REDIS_URL=redis://redis:6379/0
ALLOWED_HOSTS=*
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://107.21.145.151:3000
```

## Deployment Status
- Infrastructure: ✅ Deployed (AWS EC2)
- Backend: ✅ Active (http://107.21.145.151:8000)
- Frontend: ✅ Active (http://107.21.145.151:3000)
- Database: ✅ PostgreSQL in Docker
- Cache: ✅ Redis in Docker
- CI/CD: ✅ GitHub Actions configured

## License

This project is proprietary software.
