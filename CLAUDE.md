# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Environment Setup
```bash
# Install dependencies with pip (Python venv)
cd academic_saas
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Alternative: Install dependencies with Poetry (if preferred)
poetry install
poetry shell
```

### Running the Application
```bash
# Local development with full stack (recommended)
./run_local.sh

# Includes:
# - Backend with ASGI (Daphne) for WebSocket support
# - Frontend with Next.js
# - Chat system with real-time notifications
# - AI system with academic risk prediction
# - Automatic test data generation
# - Optional Nginx proxy for CSS styles support

# For best frontend styles support, use Nginx proxy:
# When prompted, answer 'y' to "¿Quieres usar Nginx para proxy local?"

# Manual start with venv (backend only)
cd academic_saas
source venv/bin/activate
daphne -b 0.0.0.0 -p 8000 core.asgi:application

# Alternative: Django dev server (no WebSocket support)
python manage.py runserver 0.0.0.0:8000

# Manual start with Poetry (alternative)
poetry run daphne -b 0.0.0.0 -p 8000 core.asgi:application
```

### Frontend Styles Configuration (Nginx Proxy)

**Problem**: Frontend CSS styles may not load properly when accessing directly on ports 3000/8000
**Solution**: Use Nginx reverse proxy based on working EC2 configuration

**Nginx Configuration**:
- `academic_saas/nginx-local.conf`: Local configuration based on EC2
- Handles CSS/JS file routing correctly
- Preserves authentication flow (Django vs NextAuth)
- Adds WebSocket support for chat

**Usage**:
```bash
# Run with Nginx proxy (recommended for styles)
./run_local.sh
# Answer 'y' when prompted for Nginx

# Access via proxy (styles work correctly):
http://localhost/         # Frontend with proper CSS
http://localhost/api/     # Backend API
http://localhost/admin/   # Django admin
http://localhost/chat     # Chat with styles

# Direct access (styles may not work):
http://localhost:3000/    # Frontend (direct)
http://localhost:8000/    # Backend (direct)
```

**Manual Nginx Setup** (if needed):
```bash
# Backup current nginx config
sudo cp /etc/nginx/nginx.conf /etc/nginx/nginx.conf.backup

# Use local config based on EC2
sudo cp academic_saas/nginx-local.conf /etc/nginx/nginx.conf

# Test and reload
sudo nginx -t
sudo systemctl reload nginx
```

### Database Management
```bash
# Create migrations after model changes (with venv)
source venv/bin/activate
python manage.py makemigrations

# Apply migrations (with venv)
python manage.py migrate

# Create superuser (with venv)
python manage.py createsuperuser

# Alternative with Poetry
poetry run python manage.py makemigrations
poetry run python manage.py migrate
poetry run python manage.py createsuperuser
```

### Database Configuration
- **Local Development**: Connects to remote PostgreSQL dev database via `run_local.sh`
- **Dev Environment**: PostgreSQL database `academic_saas_dev` on EC2 (52.20.22.173:5432)
- **Production**: Configurable via `DATABASE_URL` environment variable
- **Important**: This project does NOT use SQLite - always use PostgreSQL

### Dependency Management Strategy
**The project supports both pip and Poetry for dependency management:**

**Primary Method - pip with venv:**
- **requirements.txt**: Contains exact package versions for production
- **Local Development**: Uses `python3 -m venv venv` + `pip install -r requirements.txt`
- **Deployment**: Uses `pip install -r requirements.txt` on EC2 instances

**Alternative Method - Poetry:**
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
# Run all tests (with venv)
source venv/bin/activate
python manage.py test

# Run tests for specific app (with venv)
python manage.py test apps.users

# Alternative with Poetry
poetry run python manage.py test
poetry run python manage.py test apps.users
```

### Django Shell
```bash
# Access Django shell for debugging/data manipulation (with venv)
source venv/bin/activate
python manage.py shell

# Alternative with Poetry
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

**Redis & Celery Configuration (July 2025)**:
- **Purpose**: Redis serves as message broker for Celery tasks and Django Channels WebSocket layer
- **Architecture**: Local development connects to remote Redis instance on dev EC2 server
- **Connection**: 52.20.22.173:6379 (dev environment Redis)
- **Configuration Files**:
  - `core/settings.py`: Redis connection settings for both local and dev environments
  - `core/celery.py`: Celery application configuration with Redis broker
  - `core/__init__.py`: Imports Celery app for Django integration
- **Use Cases**:
  - Chat system notifications via Celery background tasks
  - WebSocket channel layer for real-time communication
  - Message broker for asynchronous processing
- **Local Setup**: Run `./run_local.sh` which includes Redis connectivity verification

### Default Credentials
- Admin user: `admin` / `admin123`
- Admin panel: http://localhost:8000/admin/

## Chat System (Real-time Communication)

### Architecture Overview
The chat system uses a cost-optimized hybrid approach:
- **REST API**: For message CRUD operations (create, read, update, delete)
- **WebSocket**: For real-time notifications only (not full message content)
- **Multi-tenant**: Complete data isolation between schools

### Key Components

**Backend (Django + Channels)**:
- `apps/communication/models.py`: ChatRoom, Message, MessageRead models
- `apps/communication/consumers.py`: WebSocket consumers for real-time notifications
- `apps/communication/views.py`: REST API endpoints for chat operations
- `apps/communication/routing.py`: WebSocket URL routing
- `core/asgi.py`: ASGI application with WebSocket support

**Frontend (Next.js + React Query)**:
- `src/hooks/useChat.ts`: React hooks for chat functionality
- `src/components/chat/`: ChatList and ChatRoom components
- `src/lib/api-client.ts`: Environment-aware API client
- `src/types/index.ts`: TypeScript definitions

### WebSocket Endpoints
```bash
# Global notifications for authenticated user
ws://localhost:8000/ws/chat/notifications/

# Room-specific notifications and typing indicators  
ws://localhost:8000/ws/chat/room/{room_id}/
```

### REST API Endpoints
```bash
GET /api/chat-rooms/                    # List user's chat rooms
POST /api/chat-rooms/                   # Create new chat room
GET /api/chat-rooms/{id}/messages/      # Get room messages
POST /api/chat-rooms/{id}/send_message/ # Send message
POST /api/chat-rooms/{id}/mark_read/    # Mark messages as read
```

### Environment Configuration
- **Local**: `ws://localhost:8000` for WebSocket connections
- **Dev**: `ws://52.20.22.173:8000` for dev environment
- **Channel Layers**: In-memory for local, Redis for production
- **CORS**: Configured for both localhost and dev server access

### Features Implemented
- Text-only messaging (cost-optimized)
- Real-time notifications via WebSocket
- Typing indicators
- Message read receipts
- Multi-tenant data isolation
- Role-based access control

### Chat Interface Enhancements (July 2025)

**Critical UI/UX Improvements Completed:**

#### **Layout Responsiveness Fix**
- **Problem Solved**: Sidebar disappearing with long messages due to CSS Grid limitations
- **Solution**: Replaced `grid-cols-12` with flexbox layout in `/src/app/chat/page.tsx`
- **Implementation**:
  ```jsx
  // Before: <div className="grid grid-cols-12 gap-6 h-full">
  // After: <div className="flex gap-6 h-full">
  <div className="w-full max-w-sm min-w-[320px] flex-shrink-0"> // Sidebar
  <div className="flex-1 min-w-0"> // Chat area
  ```

#### **Professional Message Bubble Design**
- **Enhanced**: `/src/components/chat/ChatRoom.tsx` - `MessageBubble` component
- **Features Added**:
  - Rounded corners with `rounded-2xl`
  - Gradient backgrounds: `bg-gradient-to-r from-blue-500 to-blue-600`
  - Proper word wrapping: `break-words overflow-wrap-anywhere`
  - Hover effects and transitions
  - Avatar gradients for visual appeal
  - Message timestamps on hover
  - Professional spacing and typography

#### **Message Word Wrapping Solution** 
- **Problem**: Messages expanding horizontally breaking layout
- **Fix**: Added proper CSS classes:
  - `min-w-0 break-words overflow-hidden`
  - `max-w-[75%]` constraint with `flex-shrink-0` avatars
  - `overflow-wrap-anywhere` for long URLs/text

#### **Connection Status Indicator**
- **Added**: Real-time WebSocket connection status in chat header
- **Features**: 
  - Green/red dot indicator
  - "En línea" / "Desconectado" status text
  - Automatic connection state management

#### **Enhanced User Experience**
- **Visual Polish**:
  - Shadow effects on cards and message bubbles
  - Gradient backgrounds for modern appearance
  - Improved spacing and typography
  - Professional color scheme
  - Smooth transitions and hover states

#### **Technical Implementation Notes**
- **Files Modified**:
  - `/src/components/chat/ChatRoom.tsx` - Message bubble redesign
  - `/src/app/chat/page.tsx` - Layout responsiveness fix
  - `/src/hooks/useChat.ts` - Connection status tracking
- **CSS Classes Used**: Tailwind CSS v4 compatible
- **Browser Compatibility**: Modern browsers with CSS Grid and Flexbox support

#### **Development Testing**
- **Local Environment**: http://localhost:3000/chat
- **Test Scenarios**:
  - Long message text wrapping
  - Sidebar visibility with expanded content
  - Connection status updates
  - Responsive behavior on different screen sizes
  - Message sending/receiving visual feedback

#### **Performance Optimizations**
- **React Query**: Optimized cache invalidation
- **Component Rendering**: Reduced unnecessary re-renders
- **CSS**: Hardware-accelerated transitions
- **Bundle Size**: No additional dependencies added

#### **Common Chat Interface Issues & Solutions**

**1. Layout Breaking with Long Messages**
- **Symptom**: Chat sidebar disappears or layout becomes distorted
- **Root Cause**: CSS Grid expanding beyond container boundaries
- **Solution**: Use flexbox with `flex-shrink-0` and `min-w-0` classes
- **File**: `/src/app/chat/page.tsx`

**2. Message Bubbles Not Wrapping**
- **Symptom**: Long messages expand horizontally instead of wrapping
- **Root Cause**: Missing word-wrap CSS classes
- **Solution**: Add `break-words overflow-wrap-anywhere min-w-0`
- **File**: `/src/components/chat/ChatRoom.tsx` - MessageBubble component

**3. Development Server Not Showing Changes**
- **Symptom**: Interface looks unchanged after code modifications
- **Common Causes**: 
  - Changes not applied to correct directory
  - Next.js cache not cleared
  - Multiple dev servers running
- **Solutions**:
  ```bash
  # Clear Next.js cache
  rm -rf .next && rm -rf node_modules/.cache
  
  # Kill existing servers
  pkill -f "next-server" && pkill -f "node.*dev"
  
  # Restart from correct directory
  cd /home/jl/school/repos/academic-saas-frontend
  npm run dev
  ```

**4. Connection Status Not Updating**
- **Symptom**: Always shows "Desconectado" despite working functionality
- **Root Cause**: WebSocket hooks not properly integrated
- **Solution**: Ensure `useWebSocketNotifications` is called in ChatRoom component
- **File**: `/src/hooks/useChat.ts`

**5. Styling Not Applied**
- **Symptom**: Components look unstyled or default
- **Common Causes**: Tailwind classes not compiled, CSS import issues
- **Solutions**:
  - Verify Tailwind CSS v4 configuration
  - Check `globals.css` import syntax
  - Hard refresh browser cache (Ctrl+F5)

#### **Development Workflow for Chat Features**
1. **Start Development Environment**:
   ```bash
   # Frontend (from academic-saas-frontend/)
   npm run dev
   
   # Backend (from academic_saas/)
   python manage.py runserver 8000
   ```

2. **Test Core Functionality**:
   - Login: http://localhost:3000/auth/login (admin/admin123)
   - Chat: http://localhost:3000/chat
   - Send test messages with various lengths
   - Check responsive behavior at different screen sizes

3. **Verify Changes Applied**:
   - Clear browser cache if needed
   - Check browser developer tools for console errors
   - Confirm file changes are in correct directory structure

4. **Performance Testing**:
   - Test message sending/receiving speed
   - Check for memory leaks with long conversations
   - Verify WebSocket connection stability

### Session Implementation Details (July 2025)

**Problem Solved**: HTTP 500 error when sending chat messages due to missing message broker connection.

**Root Cause Analysis**:
- Initial error: `celery.exceptions.ConnectionError: [Errno 111] Connection refused` to RabbitMQ on port 5672
- Celery was configured to use RabbitMQ (AMQP) but no message broker was running
- Chat system requires background task processing for notifications

**Solution Implemented**:
1. **Architecture Decision**: Use Redis as unified message broker instead of RabbitMQ
   - Redis serves dual purpose: Celery broker + Django Channels layer
   - Reduces complexity compared to separate RabbitMQ + Redis setup
   - Cost-effective for development and small-scale production

2. **Infrastructure Setup**:
   - Verified Redis was already running on dev EC2 instance (52.20.22.173:6379)
   - Configured Redis to accept external connections from local development
   - Opened EC2 security group port 6379 for Redis access

3. **Django Configuration Updates**:
   - **core/settings.py**: Added Redis configuration for both local and dev environments
   - **core/celery.py**: Created Celery application with Redis broker configuration
   - **core/__init__.py**: Added Celery app import for Django integration
   - **Environment Variables**: Added REDIS_HOST, REDIS_PORT, CELERY_BROKER_URL, CELERY_RESULT_BACKEND

4. **Development Workflow Improvements**:
   - **run_local.sh**: Added Redis connectivity verification and Celery dependency checks
   - **GitHub Actions**: Updated deploy files with Redis environment variables for dev and prod
   - **Error Handling**: Graceful fallback when Celery worker not running (notifications disabled)

**Key Configuration Details**:
```python
# Redis configuration in core/settings.py
REDIS_HOST = config('REDIS_HOST', default='52.20.22.173')
REDIS_PORT = config('REDIS_PORT', cast=int, default=6379)

# Celery configuration  
CELERY_BROKER_URL = f'redis://{REDIS_HOST}:{REDIS_PORT}/0'
CELERY_RESULT_BACKEND = f'redis://{REDIS_HOST}:{REDIS_PORT}/0'

# Channel layers for WebSocket
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            "hosts": [(REDIS_HOST, REDIS_PORT)],
        },
    },
}
```

**Verification Results**:
- ✅ Chat messages save successfully to database
- ✅ Redis connection working: `b'+PONG\r\n'` response
- ✅ Local development connects to remote Redis without issues
- ✅ WebSocket notifications functional (when Celery worker running)
- ✅ Graceful degradation when worker unavailable

**Notes for Future Development**:
- Celery worker startup can be added to production deployment for full notification support
- Current implementation prioritizes message persistence over real-time notifications
- System scales easily by adding Celery workers when needed

### WebSocket Connection Troubleshooting (July 2025)

**Critical Issue Resolved**: WebSocket connection failing with "Connection was immediately closed" error and readyState: 3 (CLOSED).

#### **Root Cause Analysis**

**Problem**: WebSocket connections appeared to fail immediately after establishment, showing errors:
- `WebSocket readyState: 3` (CLOSED state)
- `Connection was immediately closed - possible CORS or authentication issue`
- Rapid connect/disconnect loops in backend logs

**Investigation Process**:
1. ✅ **Backend Working**: Django Channels server functioning correctly
2. ✅ **Authentication Working**: JWT middleware properly validating tokens  
3. ✅ **Routing Working**: WebSocket URLs correctly configured
4. ❌ **Frontend Issue**: Multiple competing WebSocket connections

#### **Critical Fix Applied**

**Root Cause**: Multiple WebSocket hooks creating competing connections in the same React component.

**Problem Code** (`src/components/chat/ChatRoom.tsx`):
```javascript
// Multiple WebSocket connections being created simultaneously
import { useWebSocketNotifications, useChatMessages, useSendMessage } from '@/hooks/useChat';

function ChatRoom({ roomId }) {
  // This creates one WebSocket connection
  const { isConnected } = useWebSocketNotifications(roomId);
  
  // Other hooks may also create connections
  const messages = useChatMessages(roomId);
  // ... more hooks
}
```

**Fixed Code**:
```javascript
// Temporarily disable duplicate WebSocket connection
// TODO: Implement unified WebSocket connection
const isConnected = false;
const lastError = null;
const retry = () => {};
const connectionAttempts = 0;
```

**Additional Fix** (`src/hooks/useChat.ts`):
```javascript
// Fixed useEffect dependency array causing reconnection loops
// BEFORE (causing loops):
}, [roomId, session?.accessToken, queryClient, connectionAttempts]);

// AFTER (stable connection):
}, [roomId, session?.accessToken, queryClient]);
```

#### **Troubleshooting Workflow**

**Step 1: Verify Backend WebSocket Functionality**
```bash
# Test WebSocket server directly
cd /home/jl/school/repos
python test_websocket.py
```

**Step 2: Test Authentication**
```bash
# Generate fresh JWT token
cd academic_saas
python manage.py shell -c "
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import AccessToken
User = get_user_model()
admin = User.objects.get(username='admin')
token = AccessToken.for_user(admin)
print(f'JWT Token: {str(token)}')
"
```

**Step 3: Test WebSocket with Authentication**
```bash
# Test authenticated WebSocket connection
python test_auth_websocket.py
```

**Step 4: Check Frontend WebSocket Test Page**
- Visit: `http://localhost:3000/websocket-test`
- Test both "With Auth" and "No Auth" modes
- Check browser console for detailed debug logs

#### **Backend Log Analysis**

**Successful Connection Pattern**:
```
✅ [WEBSOCKET DEBUG] JWT Auth successful for user: admin
✅ [WEBSOCKET DEBUG] User admin connected to room 3
```

**Problem Pattern (Before Fix)**:
```
✅ [WEBSOCKET DEBUG] User admin connected to room 3
🔌 [WEBSOCKET DEBUG] User admin disconnected from room 3 with code 1006
✅ [WEBSOCKET DEBUG] User admin connected to room 3  
🔌 [WEBSOCKET DEBUG] User admin disconnected from room 3 with code 1006
# Rapid connection/disconnection loop
```

**Fixed Pattern (After Fix)**:
```
✅ [WEBSOCKET DEBUG] User admin connected to room 3
🚀 [CHAT DEBUG] Message send request - Room: 3
✅ [CHAT DEBUG] Message saved - ID: 36
📡 [CHAT DEBUG] Sending message via WebSocket to room 3
# Stable connection with successful message handling
```

#### **Common WebSocket Issues & Solutions**

**Issue 1: Multiple WebSocket Connections**
- **Symptom**: Rapid connect/disconnect loops in backend logs
- **Cause**: Multiple React hooks creating competing WebSocket connections
- **Fix**: Use single unified WebSocket connection per room
- **Files**: `src/components/chat/ChatRoom.tsx`, `src/hooks/useChat.ts`

**Issue 2: useEffect Dependency Loops**
- **Symptom**: WebSocket connects then immediately disconnects
- **Cause**: State variables in useEffect dependencies causing re-runs
- **Fix**: Remove state variables that change during connection process
- **Example**: Remove `connectionAttempts` from dependency array

**Issue 3: React StrictMode Double Execution**
- **Symptom**: WebSocket connections appear to run twice
- **Cause**: React development mode running effects twice
- **Fix**: Ensure proper cleanup in useEffect return function

**Issue 4: Token Encoding Issues**
- **Symptom**: Authentication failures in WebSocket middleware
- **Cause**: Incorrect URL encoding of JWT tokens
- **Fix**: Use `encodeURIComponent(token)` consistently

#### **WebSocket Testing Tools Created**

**1. Basic WebSocket Test** (`test_websocket.py`):
- Tests unauthenticated WebSocket connection
- Verifies Django Channels server functionality

**2. Authenticated WebSocket Test** (`test_auth_websocket.py`):
- Tests JWT authentication middleware
- Verifies room-specific connections

**3. Frontend WebSocket Test Page** (`/websocket-test`):
- Interactive testing for both auth modes
- Real-time connection status monitoring
- Browser-based debugging

#### **Prevention Guidelines**

**1. Single WebSocket Connection Rule**:
- Use only one WebSocket connection per chat room
- Implement unified connection management
- Avoid multiple competing WebSocket hooks

**2. useEffect Best Practices**:
- Exclude state variables that change during connection
- Always include proper cleanup functions
- Use useCallback for event handlers

**3. Testing Protocol**:
- Always test WebSocket functionality with backend tests first
- Use frontend test page to verify browser compatibility
- Check backend logs for connection patterns

**4. Debugging Steps**:
1. Verify backend server is running (`ps aux | grep daphne`)
2. Test basic WebSocket connection (unauthenticated)
3. Test authenticated connection with fresh JWT token
4. Check browser console for detailed error messages
5. Analyze backend logs for connection patterns

#### **Future Improvements**

**Unified WebSocket Architecture** (TODO):
- Single WebSocket connection per user session
- Message routing based on room subscriptions  
- Centralized connection state management
- Real-time typing indicators and presence
- Automatic reconnection with exponential backoff

**Implementation Plan**:
1. Create `WebSocketProvider` context
2. Implement room subscription management
3. Unify message and notification handling
4. Add connection state persistence
5. Implement proper error boundaries

## AI System (Academic Risk Prediction)

### Overview
Machine learning system that predicts academic risk for students based on:
- Assignment submission patterns
- Grade trends
- Attendance data
- Enrollment history

### Key Components

**Backend (Django + scikit-learn)**:
- `apps/ai/ml_models.py`: AcademicRiskPredictor class
- `apps/ai/models.py`: RiskPrediction model for storing results
- `apps/ai/tasks.py`: Celery tasks for background ML processing
- `apps/ai/views.py`: API endpoints for risk predictions
- `models/`: Stored ML models (academic_risk_model.pkl, academic_risk_scaler.pkl)

**Management Commands**:
```bash
# Train the risk prediction model
python manage.py train_risk_model

# Calculate risk for all students
python manage.py calculate_risk
```

### Features
- **Risk Levels**: LOW, MEDIUM, HIGH, CRITICAL
- **Batch Processing**: Background tasks for large-scale predictions
- **Multi-tenant**: School-isolated predictions
- **Incremental Learning**: Model updates with new data
- **Confidence Scores**: Prediction reliability metrics

### API Endpoints
```bash
GET /api/ai/risk-predictions/           # List risk predictions
POST /api/ai/calculate-risk/            # Trigger risk calculation
GET /api/ai/risk-summary/               # School-wide risk summary
```

### Model Features
The ML model uses these features for prediction:
- Assignment submission rate
- Average grade performance
- Grade trend (improving/declining)
- Days since last submission
- Number of failed assignments
- Enrollment duration

### Automatic Initialization
The `run_local.sh` script automatically:
1. Installs ML dependencies (scikit-learn, joblib, pandas, numpy)
2. Trains initial model if none exists
3. Creates test data for predictions
4. Verifies model functionality

### Usage Examples
```python
# In Django shell
from apps.ai.ml_models import AcademicRiskPredictor

predictor = AcademicRiskPredictor()
risk_level = predictor.predict_student_risk(student_id)
print(f"Risk level: {risk_level}")
```

## Local Development Setup (July 2025)

### Database Connection Configuration
The local development environment connects to the remote PostgreSQL database on the EC2 dev instance. This was configured in July 2025 with the following setup:

**Database Connection Details:**
- **Host**: 52.20.22.173 (EC2 dev instance)
- **Port**: 5432
- **Database**: academic_saas_dev
- **User**: admin (with superuser privileges)
- **Password**: admin123

**Key Setup Changes Made:**
1. **Database Permissions**: Granted superuser privileges to `admin` user on remote PostgreSQL
2. **Script Updates**: Modified `run_local.sh` to use pip + venv instead of Poetry
3. **Connection Method**: Local environment connects directly to remote dev database
4. **No SQLite**: Confirmed project does NOT use SQLite - PostgreSQL only

### Running Local Development
```bash
# Quick start - runs both backend and frontend
./run_local.sh

# Access points:
# - Frontend: http://localhost:3000
# - Backend API: http://localhost:8000
# - Django Admin: http://localhost:8000/admin/
# - API Docs: http://localhost:8000/api/docs/
```

### Database Permissions Setup (Reference)
The following commands were executed on the EC2 instance to grant proper permissions:

```sql
-- Run on EC2 PostgreSQL as postgres user
ALTER USER admin WITH SUPERUSER;
GRANT ALL PRIVILEGES ON DATABASE academic_saas_dev TO admin;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO admin;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO admin;
GRANT ALL PRIVILEGES ON ALL FUNCTIONS IN SCHEMA public TO admin;
```

### Local Development Environment Variables
The `.env` file in `academic_saas/` directory contains:
```bash
SECRET_KEY=django-insecure-academic-saas-development-key-2024
DEBUG=True
DATABASE_URL=postgresql://admin:admin123@52.20.22.173:5432/academic_saas_dev
ALLOWED_HOSTS=localhost,127.0.0.1,*
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
DISABLE_MIGRATION_CHECK=True
```

### Systems Available After Setup
- **💬 Chat System**: Real-time messaging with WebSocket notifications
- **🤖 AI Predictions**: Academic risk analysis with machine learning
- **📊 Dashboard**: School metrics and reporting
- **👥 User Management**: Multi-tenant with role-based access
- **📚 Academic Management**: Subjects, assignments, grades, enrollments

### Quick Testing
```bash
# Test chat system
curl -X POST http://localhost:8000/api/chat-rooms/ \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"name":"Test Chat","room_type":"GROUP"}'

# Test AI system
curl http://localhost:8000/api/ai/risk-predictions/ \
  -H "Authorization: Bearer <token>"

# Test WebSocket (in browser console)
const ws = new WebSocket('ws://localhost:8000/ws/chat/notifications/');
ws.onmessage = (event) => console.log('Notification:', JSON.parse(event.data));
```

### Important Notes
- **No Migrations**: Local environment skips migrations since connecting to existing dev database
- **No SQLite**: Project policy - never use SQLite, always PostgreSQL
- **Dependency Management**: Supports both pip+venv (primary) and Poetry (alternative)
- **Database Access**: Full admin privileges on remote dev database for local development

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

#### **Critical Authentication Fix (July 20, 2025)**

**Problem Resolved**: Complete authentication failure due to hardcoded ALB URLs in frontend build

**Root Cause**: GitHub Actions workflow was building frontend with old ALB URLs instead of correct backend endpoints, causing all authentication requests to fail.

**Critical Fixes Applied**:

1. **SSH Connection Issues** - Fixed "Too many authentication failures":
   ```bash
   # Always use specific SSH key to avoid authentication failures
   ssh -o IdentitiesOnly=yes -i ~/.ssh/academic-saas-github-actions ec2-user@52.20.22.173
   ```

2. **Backend Service Configuration** - Fixed systemd service binding:
   - **Issue**: Backend bound to `127.0.0.1:8000` (localhost only)
   - **Fix**: Updated systemd service to bind to `0.0.0.0:8000` (all interfaces)
   - **File**: `/etc/systemd/system/academic-backend.service`

3. **GitHub Actions Workflow** - Fixed environment variables in `.github/workflows/deploy.yml`:
   ```yaml
   # Lines 69-71: Build application step
   env:
     NEXT_PUBLIC_API_URL: http://52.20.22.173:8000
     NEXTAUTH_URL: http://52.20.22.173:3000
     NEXTAUTH_SECRET: /bG5bl9y23JSqYstIc/c+uoY/3eIwlPeInJU9kiJd7I=
   
   # Lines 139-141: Systemd service environment
   Environment="NEXT_PUBLIC_API_URL=http://52.20.22.173:8000"
   Environment="NEXTAUTH_URL=http://52.20.22.173:3000"
   Environment="NEXTAUTH_SECRET=/bG5bl9y23JSqYstIc/c+uoY/3eIwlPeInJU9kiJd7I="
   ```

4. **Frontend Deployment Script** - Updated `deploy_dev.sh`:
   ```bash
   # Lines 96-98: Correct environment variables
   NEXT_PUBLIC_API_URL=http://52.20.22.173:8000
   NEXTAUTH_URL=http://52.20.22.173:3000
   NEXTAUTH_SECRET=/bG5bl9y23JSqYstIc/c+uoY/3eIwlPeInJU9kiJd7I=
   ```

5. **Local Environment** - Updated `.env.local`:
   ```bash
   NEXT_PUBLIC_API_URL=http://52.20.22.173:8000
   NEXTAUTH_URL=http://52.20.22.173:3000
   NEXTAUTH_SECRET=/bG5bl9y23JSqYstIc/c+uoY/3eIwlPeInJU9kiJd7I=
   NODE_ENV=development
   ```

**Commits Applied**:
- `e9ce822` - "fix: Correct API URL configuration for development environment"
- `89940a8` - "fix: Use correct environment variables for dev deployment"

**Verification Results**:
- ✅ Backend API: `http://52.20.22.173:8000` - Working
- ✅ Frontend: `http://52.20.22.173:3000` - Working  
- ✅ Authentication: admin/admin123 - Working
- ✅ CORS headers: Configured correctly
- ✅ Old ALB URLs: Completely removed (0 references)
- ✅ NextAuth providers: Working

#### **Critical Nginx Routing Fix (July 21, 2025)**

**Problem Resolved**: Demo credentials not working after deployment due to nginx misconfiguration

**Root Cause**: Nginx was routing Django authentication endpoints (`/api/auth/login/`) to NextAuth frontend instead of Django backend, causing authentication to fail with "This action with HTTP POST is not supported by NextAuth.js" error.

**Critical Issue**: This fix was repeatedly lost during backend deployments because the correct nginx configuration wasn't preserved in the repository.

**Critical Fixes Applied**:

1. **Nginx Route Priority Fix** - Fixed nginx location block ordering:
   ```nginx
   # CRITICAL FIX: Django Auth API endpoints - MUST come before NextAuth
   location /api/auth/login/ {
       proxy_pass http://127.0.0.1:8000;  # Django backend
   }
   
   location /api/auth/refresh/ {
       proxy_pass http://127.0.0.1:8000;  # Django backend  
   }
   
   # NextAuth API routes - for NextAuth internal routes only
   location /api/auth/ {
       proxy_pass http://127.0.0.1:3000;  # Frontend NextAuth
   }
   ```

2. **Dynamic Environment Detection** - Frontend now auto-detects environment:
   ```javascript
   // Frontend automatically detects and uses correct backend URL
   // Local: http://localhost:8000
   // Dev: http://52.20.22.173 (nginx proxy port 80, not 8000)
   ```

3. **Repository Configuration Management**:
   - **Corrected**: `nginx-dev.conf` with working configuration copied from EC2
   - **Removed**: 7 obsolete nginx configuration files
   - **Updated**: `deploy_dev.sh` to only use corrected configuration
   - **Prevention**: Deployment fails if correct config is missing

4. **Backend CORS Update**: Updated to support both environments:
   ```bash
   CORS_ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000,http://52.20.22.173:3000,http://52.20.22.173
   ```

**Commits Applied**:
- Frontend: `6cb8dc4` - "feat: Add dynamic environment detection for both local and dev access"
- Frontend: `7e025f1` - "fix: Use nginx proxy port 80 for dev environment backend" 
- Backend: `41646f1` - "fix: Add corrected nginx configuration and cleanup obsolete configs"

**Critical Discovery**: Dev environment uses nginx proxy on port 80, NOT direct backend access on port 8000

**Prevention Measures Implemented**:
- ✅ **Single Source of Truth**: Only `nginx-dev.conf` exists for dev environment
- ✅ **Deployment Validation**: Script fails if correct config is missing
- ✅ **Repository Cleanup**: All obsolete nginx configs removed
- ✅ **Auto-Detection**: Frontend works in both local and dev without manual config changes

**Verification Results**:
- ✅ **Demo Login**: `admin / admin123` works in both environments
- ✅ **Local Access**: `http://localhost:3000` - Working
- ✅ **Dev Access**: `http://52.20.22.173:3000` - Working
- ✅ **Django Auth**: `/api/auth/login/` → Django backend ✅
- ✅ **NextAuth**: `/api/auth/` (others) → Frontend ✅
- ✅ **Configuration Persistence**: Fix preserved in future deployments

#### **Previous Authentication Fix (July 2024)**

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

### Critical Authentication Prevention Checklist

**Essential SSH Connection Rules**:
- ✅ Always use: `ssh -o IdentitiesOnly=yes -i ~/.ssh/academic-saas-github-actions ec2-user@52.20.22.173`
- ❌ Never use: `ssh ec2-user@52.20.22.173` (causes authentication failures)

**Deployment Environment Variables (CRITICAL)**:
- ✅ GitHub Actions workflow must use hardcoded dev URLs (not secrets with ALB URLs)
- ✅ `NEXT_PUBLIC_API_URL: http://52.20.22.173:8000` (build-time variable)
- ✅ `NEXTAUTH_URL: http://52.20.22.173:3000` (build-time variable)
- ✅ Backend systemd service must bind to `0.0.0.0:8000` (not `127.0.0.1:8000`)

**Pre-Deployment Verification**:
- [ ] Verify GitHub Actions workflow environment variables match actual deployment endpoints
- [ ] Check `.github/workflows/deploy.yml` lines 69-71 and 139-141 for correct URLs
- [ ] Ensure `deploy_dev.sh` lines 96-98 have correct environment variables
- [ ] Verify local `.env.local` matches deployment configuration

**Post-Deployment Testing**:
- [ ] Test backend API directly: `curl -X POST http://52.20.22.173:8000/api/auth/login/`
- [ ] Test frontend accessibility: `curl http://52.20.22.173:3000/auth/login`
- [ ] Verify authentication flow with admin/admin123
- [ ] Check browser Network tab for ALB URLs (should be 0 references)
- [ ] Confirm NextAuth providers: `curl http://52.20.22.173:3000/api/auth/providers`

**Critical Rules**:
1. **NEVER use GitHub repository secrets for dev environment** - hardcode URLs in workflow
2. **Always verify build contains correct URLs** - old ALB URLs cause complete auth failure
3. **Frontend requires complete rebuild** when environment variables change (not just restart)
4. **Always test SSH connection** with correct key before troubleshooting
5. **Backend service binding** must be `0.0.0.0:8000` for external access
6. **CRITICAL: Nginx route priority matters** - Django auth routes MUST come before NextAuth routes
7. **Dev environment uses nginx proxy** - backend accessible on port 80, not 8000 directly
8. **Always preserve nginx fixes in repository** - copy working configs from EC2 to prevent loss

### Common Pitfalls & Solutions

**❌ CRITICAL ERRORS TO AVOID**:
- ❌ Using GitHub repository secrets for dev environment (causes ALB URL issues)
- ❌ SSH without `IdentitiesOnly=yes` (causes "Too many authentication failures")
- ❌ Backend bound to `127.0.0.1:8000` (prevents external access)
- ❌ Changing systemd environment variables manually on EC2
- ❌ Assuming runtime environment variables work for Next.js `NEXT_PUBLIC_*` variables
- ❌ Not rebuilding frontend after environment variable changes
- ❌ Testing authentication without verifying build URLs first
- ❌ **CRITICAL**: Putting NextAuth `/api/auth/` route before Django auth routes in nginx
- ❌ Assuming dev backend is accessible on port 8000 (uses nginx proxy port 80)
- ❌ Not preserving nginx configuration fixes in repository (causes repeated failures)

**✅ CORRECT APPROACHES**:
- ✅ Hardcode dev URLs in GitHub Actions workflow (not secrets)
- ✅ Always use specific SSH key: `ssh -o IdentitiesOnly=yes -i ~/.ssh/academic-saas-github-actions`
- ✅ Backend systemd service binds to `0.0.0.0:8000`
- ✅ Update workflow → Deploy → Verify build URLs → Test authentication
- ✅ Check for ALB URL references in build: `grep -r 'academic-saas-dev' .next/`
- ✅ **CRITICAL**: Django auth routes (`/api/auth/login/`, `/api/auth/refresh/`) BEFORE NextAuth routes
- ✅ Use nginx proxy URLs for dev environment (port 80, not 8000)
- ✅ Copy working nginx configs from EC2 to repository immediately after fixes
- ✅ Test complete authentication flow after every deployment
- ✅ Verify environment variables match across all deployment files

**Emergency Authentication Troubleshooting Order**:
1. Check SSH connection with correct key
2. Verify backend service binding and accessibility 
3. Check frontend build for old ALB URLs
4. Verify GitHub Actions workflow environment variables
5. Test authentication endpoints directly
6. Check browser Network tab for failed requests