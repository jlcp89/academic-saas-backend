# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Environment Setup
```bash
# Install dependencies with Poetry
poetry install

# Activate Poetry virtual environment
poetry shell

# Or run commands with Poetry
poetry run python manage.py [command]
```

### Running the Application
```bash
# Local development with PostgreSQL and Nginx
../run_local.sh

# Manual start with Poetry
poetry run python manage.py runserver 0.0.0.0:8000
```

### Database Management
```bash
# Create migrations after model changes
poetry run python manage.py makemigrations

# Apply migrations
poetry run python manage.py migrate

# Create superuser
poetry run python manage.py createsuperuser
```

### Database Configuration
- **Local Environment**: PostgreSQL database `academic_saas_local` with user `academic_saas_local`
- **Dev Environment**: PostgreSQL database `academic_saas_dev` with user `academic_saas_dev`  
- **Production**: Configurable via `DATABASE_URL` environment variable

### Dependency Management Strategy
**Poetry ensures exact version consistency across all environments:**

- **pyproject.toml**: Defines dependency ranges and project metadata
- **poetry.lock**: Locks exact versions (commit this file to git)
- **Local**: Uses `poetry install` (includes dev dependencies for testing)
- **Dev/Prod**: Uses `poetry install --only=main --no-dev` (production only)

**Key Benefits:**
- Identical package versions between local, dev, and production
- Deterministic builds and deployments
- Easier debugging (same environment everywhere)
- Dependency vulnerability tracking

### Testing
```bash
# Run all tests
poetry run python manage.py test

# Run tests for specific app
poetry run python manage.py test apps.users
```

### Django Shell
```bash
# Access Django shell for debugging/data manipulation
poetry run python manage.py shell
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
- PostgreSQL for all environments (local, dev, production)
- Poetry for dependency management
- Optional AWS S3 storage for media files

### Default Credentials
- Admin user: `admin` / `admin123`
- Admin panel: http://localhost:8000/admin/

### GitHub Repository Secrets Configuration

**Frontend Repository Secrets Required:**

**Development Environment:**
```
NEXT_PUBLIC_API_URL=http://52.20.22.173:8000
NEXTAUTH_URL=http://52.20.22.173:3000
NEXTAUTH_SECRET=[secure-random-string]
EC2_HOST_DEV=52.20.22.173
EC2_SSH_KEY=[private-ssh-key-content]
```

**Production Environment:**
```
NEXT_PUBLIC_API_URL_PROD=http://[production-domain]:8000
NEXTAUTH_URL_PROD=http://[production-domain]:3000
NEXTAUTH_SECRET=[secure-random-string]
EC2_HOST_PROD=[production-ip-or-domain]
EC2_SSH_KEY=[private-ssh-key-content]
```

**Backend Repository Secrets Required:**

**Development Environment:**
```
EC2_HOST_DEV=52.20.22.173
EC2_SSH_KEY=[private-ssh-key-content]
DATABASE_URL_DEV=postgresql://admin:admin123@localhost:5432/academic_saas_dev
SECRET_KEY_DEV=[django-secret-key]
```

**Production Environment:**
```
EC2_HOST_PROD=[production-ip-or-domain]
EC2_SSH_KEY=[private-ssh-key-content]
DATABASE_URL_PROD=[production-database-url]
SECRET_KEY_PROD=[django-secret-key]
```

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

### CORS and Authentication Configuration

**Important**: The application uses dynamic CORS configuration to support multiple environments.

**Backend CORS Settings** (`core/settings.py`):
```python
# CORS settings - Configurable via environment variables
CORS_ALLOWED_ORIGINS = config('CORS_ALLOWED_ORIGINS', cast=lambda v: [s.strip() for s in v.split(',')], default=[
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://52.20.22.173",
    "http://52.20.22.173:3000",
])

# Additional CORS settings for development
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_ALL_ORIGINS = config('CORS_ALLOW_ALL_ORIGINS', cast=bool, default=False)
```

**Development Environment CORS Configuration**:
```bash
# Backend .env file
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000,http://52.20.22.173,http://52.20.22.173:3000
CORS_ALLOW_CREDENTIALS=True
CORS_ALLOW_ALL_ORIGINS=False
```

**Frontend API URL Configuration**:
```bash
# Development
NEXT_PUBLIC_API_URL=http://52.20.22.173:8000

# Local development  
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### Common Authentication Issues and Solutions

**Problem**: 401 Unauthorized errors during login in development environment

**Root Causes**:
1. **Incorrect API URL**: Frontend trying to connect to wrong backend port
2. **CORS Configuration**: Backend blocking requests from frontend domain
3. **Missing CORS Headers**: Authentication requests being blocked

**Solutions**:
1. **Verify API URL**: Ensure `NEXT_PUBLIC_API_URL` points to correct backend port (8000)
2. **Check CORS Settings**: Verify `CORS_ALLOWED_ORIGINS` includes frontend domain
3. **Enable Credentials**: Set `CORS_ALLOW_CREDENTIALS=True` for authentication
4. **Environment Variables**: Ensure proper configuration in deployment scripts

**Debugging Steps**:
1. Check browser Network tab for CORS errors
2. Verify backend is running on correct port
3. Confirm CORS headers in response
4. Test API endpoints directly with curl/Postman

**Deployment Checklist**:
- [ ] Backend CORS configured for frontend domain
- [ ] Frontend API URL points to correct backend port
- [ ] Environment variables set in deployment scripts
- [ ] Credentials enabled for authentication
- [ ] All domains included in CORS_ALLOWED_ORIGINS

### Development Workflow

1. **Start Both Servers with Nginx**:
   ```bash
   # Single command from project root
   ./run_local.sh
   ```

2. **Access Points (via Nginx reverse proxy)**:
   - Application: http://localhost
   - Backend API: http://localhost/api/
   - Django Admin: http://localhost/admin/
   
3. **Direct Access (development only)**:
   - Frontend: http://localhost:3000
   - Backend: http://localhost:8000
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

### Production Deployment

**Development Environment:**
- **IP Address**: 52.20.22.173
- **Backend**: http://52.20.22.173:8000
- **Frontend**: http://52.20.22.173:3000
- **Admin Panel**: http://52.20.22.173:8000/admin/

**GitHub Actions Deployment:**
- Deployments to dev environment are automatically triggered on push to `dev` branch
- Deployments to production environment are triggered when pushing to `main` branch
- Both backend and frontend use SSH direct deployment strategy
- Health checks are performed after deployment to ensure services are running correctly

### Frontend Access Troubleshooting

**Common Issue: "Can't access frontend with demo credentials"**

**Root Cause**: Environment variables in GitHub secrets pointing to localhost instead of external IP.

**Symptoms:**
- Frontend redirects to authentication but login fails
- Authentication redirects loop back to localhost URLs
- External access via 52.20.22.173 not working

**Solution:**
1. **Update GitHub Repository Secrets** (frontend repo):
   ```
   NEXT_PUBLIC_API_URL = http://52.20.22.173:8000
   NEXTAUTH_URL = http://52.20.22.173:3000
   NEXTAUTH_SECRET = [keep existing secure value]
   ```

2. **Trigger Redeployment:**
   - Make any small change to trigger dev workflow
   - Push to dev branch to redeploy with correct environment variables

3. **Verify Deployment:**
   ```bash
   # Check frontend service status
   curl -I http://52.20.22.173:3000/
   
   # Check authentication endpoint
   curl -s http://52.20.22.173:3000/api/auth/signin
   ```

**Environment Variable Requirements:**
- **Dev Environment**: Use external IP (52.20.22.173) for all URLs
- **Local Development**: Use localhost for all URLs
- **Production**: Use production domain for all URLs

**Deployment Architecture:**
- Frontend runs as Node.js service on port 3000 (systemd)
- Backend runs as Gunicorn service on port 8000 (systemd)
- Nginx proxies external traffic to both services
- Static files served through Next.js (not pre-rendered)

### Important Deployment Notes

**Both repositories do NOT use Docker:**
- All deployments use direct SSH strategy without Docker containers
- **Backend**: Uses Poetry for dependency management and direct Python execution
- **Frontend**: Builds static files and serves them through nginx
- No Docker images, containers, or docker-compose files are used in deployment

**Frontend serves through nginx (NOT PM2):**
- Frontend deployment copies built files to `/var/www/html/`
- nginx serves the static Next.js build files directly
- No Node.js process managers (PM2) are used in production
- nginx handles all static file serving and routing

## Environment Synchronization & Secrets Management

### Critical Issue: Build-time vs Runtime Variables

**Problem**: Next.js `NEXT_PUBLIC_*` variables are baked into the build at build time, not at runtime. This means:
- Changing systemd environment variables alone won't fix frontend configuration
- GitHub repository secrets must match actual deployment environment
- Frontend must be rebuilt when environment variables change

### Environment Verification Process

**Run verification script:**
```bash
./verify_environment.sh dev
```

**Manual verification commands:**
```bash
# Check frontend service environment
ssh ec2-user@52.20.22.173 "sudo systemctl show academic-frontend --property=Environment"

# Check for old URLs in build
ssh ec2-user@52.20.22.173 "grep -r 'academic-saas-dev-backend-alb' /home/ec2-user/academic-saas-frontend/.next/ 2>/dev/null | wc -l"

# Test backend authentication
curl -X POST http://52.20.22.173:8000/api/auth/login/ \
  -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"admin123"}'
```

### Required GitHub Secrets (Current Status)

**Frontend Repository (jlcp89/academic-saas-frontend)**:
```bash
# CORRECT VALUES NEEDED:
NEXT_PUBLIC_API_URL = http://52.20.22.173:8000
NEXTAUTH_URL = http://52.20.22.173:3000
NEXTAUTH_SECRET = /bG5bl9y23JSqYstIc/c+uoY/3eIwlPeInJU9kiJd7I=
EC2_HOST_DEV = 52.20.22.173
EC2_SSH_KEY = [private-ssh-key-content]

# CURRENT INCORRECT VALUES:
# NEXT_PUBLIC_API_URL = http://academic-saas-dev-backend-alb-1977961495.us-east-1.elb.amazonaws.com
# NEXTAUTH_URL = http://academic-saas-dev-frontend-alb-560850445.us-east-1.elb.amazonaws.com
```

### Step-by-Step Fix Process

1. **Update GitHub Repository Secrets**:
   - Go to GitHub repository: `jlcp89/academic-saas-frontend`
   - Settings → Secrets and variables → Actions
   - Update the secrets with correct IP addresses

2. **Trigger Redeployment**:
   ```bash
   # Make small change to trigger workflow
   echo "Deploy $(date)" >> test-deployment-trigger.txt
   git add test-deployment-trigger.txt
   git commit -m "Trigger deployment with correct environment variables"
   git push origin dev
   ```

3. **Monitor Deployment**:
   ```bash
   # Watch GitHub Actions workflow
   # Verify deployment with verification script
   ./verify_environment.sh dev
   ```

4. **Verify Fix**:
   ```bash
   # Should show 0 references to old URLs
   ssh ec2-user@52.20.22.173 "grep -r 'academic-saas-dev-backend-alb' /home/ec2-user/academic-saas-frontend/.next/ 2>/dev/null | wc -l"
   
   # Test login functionality
   # Visit: http://52.20.22.173:3000
   # Login with: admin / admin123
   ```

### Environment Consistency Rules

## Troubleshooting Authentication Issues

### Common Authentication Problems

**1. 401 Unauthorized on Login**
- **Symptoms**: Login form shows "Invalid credentials" but credentials are correct
- **Browser Network Tab**: Shows 401 response from `/api/auth/callback/credentials`
- **Root Cause**: Usually CORS configuration or incorrect API URL

**2. CORS Errors in Browser Console**
- **Symptoms**: Browser console shows CORS policy errors
- **Root Cause**: Backend not configured to allow frontend domain
- **Solution**: Update `CORS_ALLOWED_ORIGINS` in backend settings

**3. Frontend Can't Connect to Backend**
- **Symptoms**: Network errors, timeouts, or connection refused
- **Root Cause**: Incorrect `NEXT_PUBLIC_API_URL` or backend not running
- **Solution**: Verify backend port (8000) and frontend API URL configuration

### Quick Fix Commands

**Check Backend Status**:
```bash
# SSH to development server
ssh -i ~/.ssh/academic_saas_aws ubuntu@52.20.22.173

# Check backend service
sudo systemctl status academic-saas-backend

# Check backend logs
sudo journalctl -u academic-saas-backend -f

# Test backend directly
curl -X POST http://52.20.22.173:8000/api/auth/login/ \
  -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"admin123"}'
```

**Check Frontend Configuration**:
```bash
# Check frontend service
sudo systemctl status academic-frontend

# Check frontend logs
sudo journalctl -u academic-frontend -f

# Verify environment variables
cat /home/ec2-user/academic-saas-frontend/.env.local
```

**Verify CORS Configuration**:
```bash
# Check backend CORS settings
cat /home/ec2-user/academic-saas-backend/.env

# Test CORS headers
curl -H "Origin: http://52.20.22.173" \
  -H "Access-Control-Request-Method: POST" \
  -H "Access-Control-Request-Headers: Content-Type" \
  -X OPTIONS http://52.20.22.173:8000/api/auth/login/
```

### Recent Fixes Applied (July 2024)

**Problem Resolved**: 401 Unauthorized errors in development environment

**Changes Made**:

1. **Backend CORS Configuration** (`core/settings.py`):
   - Made `CORS_ALLOWED_ORIGINS` configurable via environment variables
   - Added support for development server domains
   - Enabled `CORS_ALLOW_CREDENTIALS` for authentication

2. **Frontend API URL** (`deploy_dev.sh`):
   - Fixed `NEXT_PUBLIC_API_URL` to include correct backend port (8000)
   - Changed from `http://52.20.22.173` to `http://52.20.22.173:8000`

3. **Deployment Scripts Updated**:
   - Backend: Added proper CORS environment variables
   - Frontend: Corrected API URL configuration

**Commits Applied**:
- Backend: `10b58b4` - "fix: Configurar CORS correctamente para entorno de desarrollo"
- Frontend: `98d5c2d` - "fix: Corregir URL del API en configuración de desarrollo"

### Prevention Checklist

To avoid authentication issues in future deployments:

- [ ] Always verify `NEXT_PUBLIC_API_URL` includes correct backend port
- [ ] Ensure `CORS_ALLOWED_ORIGINS` includes all frontend domains
- [ ] Test authentication flow after deployment
- [ ] Check browser Network tab for CORS errors
- [ ] Verify environment variables in deployment scripts
- [ ] Test API endpoints directly before frontend integration

1. **Never manually edit environment variables on EC2** - always use GitHub deployment
2. **Always verify secrets match deployment environment** before troubleshooting
3. **Run verification script after any deployment** to catch mismatches early
4. **Frontend requires rebuild** when environment variables change (not just restart)

### Common Pitfalls

- ❌ Changing systemd environment variables manually
- ❌ Assuming runtime environment variables work for Next.js public variables
- ❌ Not rebuilding frontend after environment variable changes
- ✅ Update GitHub secrets → Deploy → Verify
- ✅ Use verification script to catch issues early