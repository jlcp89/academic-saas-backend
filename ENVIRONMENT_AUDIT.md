# Environment Configuration Audit - Academic SaaS

## Current Status (2025-07-20)

### Development Environment (52.20.22.173)

#### Frontend Service (academic-frontend.service)
**Status**: ✅ CORRECT
```bash
NEXT_PUBLIC_API_URL=http://52.20.22.173:8000
NEXTAUTH_URL=http://52.20.22.173:3000
NEXTAUTH_SECRET=/bG5bl9y23JSqYstIc/c+uoY/3eIwlPeInJU9kiJd7I=
```

#### Backend Service (Gunicorn Process)
**Status**: ✅ RUNNING
- Process: gunicorn --bind 127.0.0.1:8000 --workers 2
- PID File: /tmp/django.pid
- Logs: /tmp/django.log

### GitHub Repository Secrets (NEEDS UPDATE)

#### Frontend Repository: jlcp89/academic-saas-frontend
**Current (INCORRECT)**:
```
NEXT_PUBLIC_API_URL = http://academic-saas-dev-backend-alb-1977961495.us-east-1.elb.amazonaws.com
NEXTAUTH_URL = http://academic-saas-dev-frontend-alb-560850445.us-east-1.elb.amazonaws.com
```

**Required (CORRECT)**:
```
NEXT_PUBLIC_API_URL = http://52.20.22.173:8000
NEXTAUTH_URL = http://52.20.22.173:3000
NEXTAUTH_SECRET = /bG5bl9y23JSqYstIc/c+uoY/3eIwlPeInJU9kiJd7I=
EC2_HOST_DEV = 52.20.22.173
EC2_SSH_KEY = [private-ssh-key-content]
```

#### Backend Repository: jlcp89/academic-saas-backend
**Required**:
```
EC2_HOST_DEV = 52.20.22.173
EC2_SSH_KEY = [private-ssh-key-content]
DATABASE_URL_DEV = postgresql://admin:admin123@localhost:5432/academic_saas_dev
SECRET_KEY_DEV = [django-secret-key]
```

## Issue Analysis

### Root Cause
1. **Build-time Variables**: `NEXT_PUBLIC_*` variables are baked into Next.js build at build time
2. **GitHub Secrets Mismatch**: Deployment uses GitHub secrets, not local environment files
3. **Load Balancer URLs**: Old AWS infrastructure URLs still in GitHub secrets

### Solution Required
1. Update GitHub repository secrets with correct IP addresses
2. Trigger redeployment to rebuild frontend with correct variables
3. Implement verification procedures to prevent future mismatches

## Verification Commands

### Check Frontend Environment
```bash
ssh ec2-user@52.20.22.173 "sudo systemctl show academic-frontend --property=Environment"
```

### Check Backend Status
```bash
ssh ec2-user@52.20.22.173 "ps aux | grep gunicorn | grep -v grep"
```

### Test API Connectivity
```bash
curl -I http://52.20.22.173:8000/api/
curl -I http://52.20.22.173:3000/
```

### Test Authentication
```bash
curl -X POST http://52.20.22.173:8000/api/auth/login/ \
  -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"admin123"}'
```