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
- Deployments to dev environment are automatically triggered on pull requests to `dev` branch
- Deployments to production environment are triggered when PRs to `main` branch are merged
- Both backend and frontend use SSH direct deployment strategy
- Health checks are performed after deployment to ensure services are running correctly

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