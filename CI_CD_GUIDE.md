# Enhanced CI/CD Pipeline Guide

## Overview

This document describes the enhanced CI/CD pipeline implemented for the Academic SaaS platform, featuring automated deployment to both development and production environments.

## Architecture

### Branch Strategy
- **`main`**: Production branch - triggers production deployment
- **`dev`**: Development branch - triggers development deployment  
- **`feature/*`**: Feature branches - trigger development deployment for testing
- **Pull Requests**: Run tests and build validation only

### Deployment Environments

#### Development Environment
- **Target**: Single EC2 instance (`DEV_INSTANCE_IP`)
- **Triggers**: Pushes to `dev` and `feature/*` branches
- **Purpose**: Testing and validation
- **Access**: http://{DEV_INSTANCE_IP}:8000

#### Production Environment  
- **Target**: Auto Scaling Group with Load Balancer
- **Triggers**: Pushes to `main` branch only
- **Purpose**: Live production system
- **Access**: Via Application Load Balancer

## Workflow Structure

### 1. Test and Build Job
**Purpose**: Validates code quality and builds Docker images

**Steps**:
- ✅ Checkout code
- ✅ Setup Python/Node.js environment
- ✅ Install dependencies
- ✅ Run tests (Django test suite / TypeScript checks)
- ✅ Code quality checks (flake8 / ESLint)
- ✅ Build and push Docker image to ECR
- ✅ Output image URI for deployment jobs

**Conditions**: Runs on all pushes and PRs

### 2. Development Deployment Job
**Purpose**: Deploy to development environment for testing

**Steps**:
- 🚀 Configure AWS credentials (development)
- 📥 Download image from ECR
- ⏹️ Stop existing container gracefully
- 🔄 Deploy new container with environment variables
- 🏥 Health check verification
- ✅ Deployment confirmation

**Conditions**: 
- Runs only on pushes to `dev` and `feature/*` branches
- Requires successful test-and-build job
- Uses development AWS credentials and secrets

### 3. Production Deployment Job
**Purpose**: Deploy to production Auto Scaling Group

**Steps**:
- 🚀 Configure AWS credentials (production)
- 📋 Get healthy instances from ASG
- 🔄 Rolling deployment to each instance
- 🏥 Health check on each instance
- 🔧 Run migrations (backend only, on one instance)
- ✅ Load balancer verification

**Conditions**:
- Runs only on pushes to `main` branch
- Requires successful test-and-build job
- Uses production AWS credentials and secrets (`*_PROD`)

### 4. Notification Job
**Purpose**: Report deployment status and provide access URLs

**Steps**:
- 📊 Summarize all job results
- 🌐 Provide access URLs
- ✅/❌ Success/failure notifications

**Conditions**: Always runs (regardless of job success/failure)

## Environment Variables & Secrets

### Development Secrets (Current)
```
AWS_ACCESS_KEY_ID
AWS_SECRET_ACCESS_KEY
DEV_INSTANCE_IP
EC2_SSH_KEY
DJANGO_SECRET_KEY
DATABASE_URL
REDIS_URL
ALLOWED_HOSTS
CORS_ALLOWED_ORIGINS
AWS_STORAGE_BUCKET_NAME
NEXT_PUBLIC_API_URL
NEXTAUTH_URL
NEXTAUTH_SECRET
```

### Production Secrets (To be created)
```
AWS_ACCESS_KEY_ID_PROD
AWS_SECRET_ACCESS_KEY_PROD
EC2_SSH_KEY_PROD
DJANGO_SECRET_KEY_PROD
DATABASE_URL_PROD
REDIS_URL_PROD
ALLOWED_HOSTS_PROD
CORS_ALLOWED_ORIGINS_PROD
AWS_STORAGE_BUCKET_NAME_PROD
NEXT_PUBLIC_API_URL_PROD
NEXTAUTH_URL_PROD
NEXTAUTH_SECRET_PROD
```

## Deployment Process

### Automated Build Process
1. **GitHub Actions Runner** downloads source code
2. **Docker Build** creates optimized production image
3. **ECR Push** uploads image to container registry
4. **Image URI** passed to deployment jobs

### Deployment Execution
1. **SSH Connection** to target instance(s)
2. **ECR Login** using AWS credentials
3. **Image Pull** downloads latest built image
4. **Environment Setup** creates secure .env files
5. **Container Deployment** with rolling restart
6. **Health Verification** confirms successful deployment

### Key Optimizations
- ⚡ **Build Once, Deploy Everywhere**: Images built in GitHub Actions
- 🔄 **Rolling Deployments**: Zero-downtime updates
- 🏥 **Health Checks**: Automatic rollback on failure
- 🔐 **Secure Secrets**: Environment-specific credentials
- 📦 **Container Registry**: Versioned deployments with rollback capability

## Security Features

### SSH Security
- Private keys stored as GitHub secrets
- SSH connections with strict host key checking disabled (controlled environment)
- Automatic cleanup of temporary SSH keys

### Container Security
- Non-root user execution
- Environment variables in secure files (`600` permissions)
- Health checks for container validation

### AWS Security
- Separate IAM credentials for dev/prod
- ECR access with minimal required permissions
- VPC security groups restricting access

## Monitoring and Troubleshooting

### Deployment Logs
- GitHub Actions provides detailed logs for each step
- Container logs available via `docker logs academic-saas-{backend|frontend}`
- SSH access to instances for debugging

### Health Check Endpoints
- **Backend**: `http://{host}:8000/admin/login/`
- **Frontend**: `http://{host}:3000/`

### Common Issues and Solutions

#### 1. ECR Login Failures
```bash
# Verify AWS credentials
aws sts get-caller-identity

# Manual ECR login
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin {ECR_REGISTRY}
```

#### 2. Container Startup Failures
```bash
# Check container logs
docker logs academic-saas-backend --tail 50

# Verify environment variables
docker exec academic-saas-backend env | grep -E "(SECRET_KEY|DATABASE_URL)"
```

#### 3. Health Check Failures
```bash
# Test endpoints manually
curl -I http://localhost:8000/admin/login/  # Backend
curl -I http://localhost:3000/             # Frontend

# Check container status
docker ps | grep academic-saas
```

## Manual Deployment Commands

### Emergency Backend Deployment
```bash
# SSH to instance
ssh -i ~/.ssh/academic_saas_aws ec2-user@{DEV_INSTANCE_IP}

# Manual deployment
./deploy-backend-dev.sh {ECR_REGISTRY} {IMAGE_URI} {ENV_VARS...}
```

### Emergency Frontend Deployment
```bash
# SSH to instance  
ssh -i ~/.ssh/academic_saas_aws ec2-user@{DEV_INSTANCE_IP}

# Manual deployment
./deploy-frontend-dev.sh {ECR_REGISTRY} {IMAGE_URI} {ENV_VARS...}
```

## Rollback Procedures

### Automatic Rollback
- Health checks fail → deployment stops
- Previous container remains running
- Manual investigation required

### Manual Rollback
```bash
# List available images
docker images | grep academic-saas

# Deploy specific version
docker run -d --name academic-saas-backend {IMAGE_TAG}
```

## Performance Metrics

### Build Times
- **Backend Build**: ~5-8 minutes (includes tests)
- **Frontend Build**: ~3-5 minutes (includes TypeScript checking)
- **Deployment**: ~2-3 minutes per environment

### Deployment Frequency
- **Development**: Every feature branch push
- **Production**: Every main branch push
- **Rollback Time**: ~2-3 minutes

## Next Steps

1. **Production Secrets**: Create `*_PROD` secrets in GitHub
2. **Load Balancer**: Configure actual ALB DNS endpoints
3. **Monitoring**: Add CloudWatch integration
4. **Notifications**: Add Slack/email notifications
5. **Blue-Green**: Implement blue-green deployment strategy

## Support and Maintenance

### Regular Tasks
- Monitor ECR storage usage
- Review deployment logs weekly
- Update GitHub Actions runners monthly
- Rotate AWS credentials quarterly

### Emergency Contacts
- **DevOps**: Check GitHub Actions status
- **Infrastructure**: AWS Console for resource health
- **Application**: Container logs and health endpoints