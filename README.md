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

## Setup Instructions

1. **Create virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment variables**:
   - Copy `.env.example` to `.env`
   - Update database credentials and other settings

4. **Run migrations**:
   ```bash
   python manage.py migrate
   ```

5. **Create superuser**:
   ```bash
   python manage.py createsuperuser
   ```

6. **Run development server**:
   ```bash
   python manage.py runserver
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

For production deployment:
1. Set `DEBUG=False` in environment variables
2. Configure PostgreSQL database
3. Set up static file serving
4. Configure ALLOWED_HOSTS
5. Use gunicorn or similar WSGI server

## License

This project is proprietary software.