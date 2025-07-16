#!/bin/bash

# Academic SaaS AWS Infrastructure Deployment Script
# This script will guide you through deploying your infrastructure to AWS

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

print_header() {
    echo -e "${BLUE}"
    echo "=========================================="
    echo "  🎓 Academic SaaS AWS Deployment"
    echo "=========================================="
    echo -e "${NC}"
}

print_step() {
    echo -e "${BLUE}📋 $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

check_prerequisites() {
    print_step "Checking prerequisites..."
    
    # Check if AWS CLI is installed
    if ! command -v aws &> /dev/null; then
        print_error "AWS CLI is not installed"
        echo "Please install AWS CLI: https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html"
        exit 1
    fi
    
    # Check if Terraform is installed
    if [ -f "./terraform" ]; then
        TERRAFORM_CMD="./terraform"
        print_success "Using local Terraform binary"
    elif command -v terraform &> /dev/null; then
        TERRAFORM_CMD="terraform"
        print_success "Using system Terraform"
    else
        print_error "Terraform is not installed"
        echo "Please install Terraform: https://learn.hashicorp.com/tutorials/terraform/install-cli"
        exit 1
    fi
    
    # Check AWS credentials
    if ! aws sts get-caller-identity &> /dev/null; then
        print_error "AWS credentials not configured"
        echo "Please run: aws configure"
        exit 1
    fi
    
    print_success "All prerequisites satisfied"
}

setup_ssh_key() {
    print_step "Setting up SSH key for EC2 access..."
    
    SSH_KEY_PATH="$HOME/.ssh/academic_saas_aws"
    
    if [ ! -f "$SSH_KEY_PATH" ]; then
        print_step "Generating new SSH key pair..."
        ssh-keygen -t rsa -b 4096 -C "academic-saas-aws" -f "$SSH_KEY_PATH" -N ""
        print_success "SSH key generated at $SSH_KEY_PATH"
    else
        print_warning "SSH key already exists at $SSH_KEY_PATH"
    fi
    
    # Set correct permissions
    chmod 600 "$SSH_KEY_PATH"
    chmod 644 "$SSH_KEY_PATH.pub"
    
    print_success "SSH key configured"
    echo "Public key: $(cat $SSH_KEY_PATH.pub)"
}

setup_terraform_backend() {
    print_step "Setting up Terraform backend..."
    
    # Check if backend.tf already exists
    if [ -f "infrastructure/terraform/backend.tf" ]; then
        print_warning "Terraform backend already configured"
        # Read existing configuration
        BUCKET_NAME=$(grep 'bucket' infrastructure/terraform/backend.tf | awk -F'"' '{print $2}')
        TABLE_NAME=$(grep 'dynamodb_table' infrastructure/terraform/backend.tf | awk -F'"' '{print $2}')
        print_success "Using existing backend configuration"
        echo "S3 Bucket: $BUCKET_NAME"
        echo "DynamoDB Table: $TABLE_NAME"
        return
    fi
    
    # Create S3 bucket for Terraform state
    BUCKET_NAME="academic-saas-terraform-state-$(date +%s)"
    REGION="us-east-1"
    
    print_step "Creating S3 bucket for Terraform state: $BUCKET_NAME"
    
    # Create bucket
    aws s3 mb s3://$BUCKET_NAME --region $REGION
    
    # Enable versioning
    aws s3api put-bucket-versioning \
        --bucket $BUCKET_NAME \
        --versioning-configuration Status=Enabled
    
    # Enable encryption
    aws s3api put-bucket-encryption \
        --bucket $BUCKET_NAME \
        --server-side-encryption-configuration '{
            "Rules": [
                {
                    "ApplyServerSideEncryptionByDefault": {
                        "SSEAlgorithm": "AES256"
                    }
                }
            ]
        }'
    
    # Create DynamoDB table for state locking
    TABLE_NAME="academic-saas-terraform-locks"
    
    print_step "Creating DynamoDB table for state locking: $TABLE_NAME"
    
    # Check if table already exists
    if aws dynamodb describe-table --table-name $TABLE_NAME --region $REGION &> /dev/null; then
        print_warning "DynamoDB table already exists: $TABLE_NAME"
    else
        aws dynamodb create-table \
            --table-name $TABLE_NAME \
            --attribute-definitions AttributeName=LockID,AttributeType=S \
            --key-schema AttributeName=LockID,KeyType=HASH \
            --provisioned-throughput ReadCapacityUnits=5,WriteCapacityUnits=5 \
            --region $REGION
    fi
    
    # Create backend configuration
    cat > infrastructure/terraform/backend.tf << EOF
terraform {
  backend "s3" {
    bucket         = "$BUCKET_NAME"
    key            = "academic-saas/terraform.tfstate"
    region         = "$REGION"
    dynamodb_table = "$TABLE_NAME"
    encrypt        = true
  }
}
EOF
    
    print_success "Terraform backend configured"
    echo "S3 Bucket: $BUCKET_NAME"
    echo "DynamoDB Table: $TABLE_NAME"
}

prepare_terraform_vars() {
    print_step "Preparing Terraform variables..."
    
    # Check if terraform.tfvars already exists
    if [ -f "infrastructure/terraform/terraform.tfvars" ]; then
        print_warning "terraform.tfvars already exists"
        read -p "Do you want to overwrite it? (yes/no): " overwrite
        if [ "$overwrite" != "yes" ]; then
            print_success "Using existing terraform.tfvars"
            return
        fi
    fi
    
    # Get AWS account ID and region
    AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
    AWS_REGION=$(aws configure get region || echo "us-east-1")
    
    # Get public SSH key content
    SSH_PUBLIC_KEY=$(cat ~/.ssh/academic_saas_aws.pub)
    
    # Create terraform.tfvars file
    cat > infrastructure/terraform/terraform.tfvars << EOF
# Academic SaaS Infrastructure Configuration
# Generated on $(date)

# Project Configuration
project_name = "academic-saas"
environment = "dev"
aws_region = "$AWS_REGION"

# Network Configuration
vpc_cidr = "10.0.0.0/16"

# Free Tier Instance Types (Development)
# IMPORTANT: Using Free Tier eligible instances
environment_config = {
  dev = {
    backend_instance_type     = "t2.micro"     # Free Tier: 750 hours/month
    frontend_instance_type    = "t2.micro"    # Free Tier: 750 hours/month
    db_instance_class        = "db.t3.micro"   # Free Tier: 750 hours/month
    redis_node_type          = "cache.t3.micro" # Free Tier: 750 hours/month
    backend_min_size         = 1
    backend_max_size         = 1               # Keep at 1 to stay in free tier
    backend_desired_capacity = 1
    frontend_min_size        = 1
    frontend_max_size        = 1               # Keep at 1 to stay in free tier
    frontend_desired_capacity = 1
  }
}

# Cost Control - CRITICAL FOR LOW COST
monthly_budget_limit = 50          # Reducido a $50/mes
ec2_budget_limit = 20              # Límite EC2
rds_budget_limit = 15              # Límite RDS
budget_alert_emails = ["admin@yourdomain.com"]
cost_anomaly_email = "admin@yourdomain.com"
anomaly_threshold = 50

# Database Configuration (Free Tier)
db_allocated_storage = 20
db_max_allocated_storage = 20
db_name = "academic_saas_dev"
db_username = "academic_user"

# Cost Optimization - CRITICAL SETTINGS
use_nat_instance = true            # NAT Instance ($4/mes) vs NAT Gateway ($32/mes)
use_nat_instance_ha = false        # No HA para desarrollo (ahorra costos)
use_public_subnets = false         # Mantener seguridad
enable_spot_instances = false      # No spot para free tier
enable_scheduled_scaling = true    # Auto-apagar noches/fines de semana

# S3 Configuration
s3_lifecycle_enabled = true
s3_transition_to_ia_days = 30
s3_transition_to_glacier_days = 90

# SSH Key (automatically generated)
# Public key will be imported to AWS
EOF

    print_success "Terraform variables prepared"
}

deploy_infrastructure() {
    print_step "Deploying infrastructure with Terraform..."
    
    cd infrastructure/terraform
    
    # Initialize Terraform
    print_step "Initializing Terraform..."
    $TERRAFORM_CMD init
    
    # Validate configuration
    print_step "Validating Terraform configuration..."
    $TERRAFORM_CMD validate
    
    # Plan deployment
    print_step "Planning infrastructure deployment..."
    $TERRAFORM_CMD plan -out=tfplan
    
    # Ask for confirmation
    echo ""
    print_warning "Ready to deploy AWS infrastructure. This will create:"
    echo "- VPC with public/private subnets"
    echo "- EC2 instances (free tier)"
    echo "- RDS PostgreSQL database (free tier)"
    echo "- ElastiCache Redis (free tier)"
    echo "- Load balancers and security groups"
    echo "- Cost monitoring and budgets"
    echo ""
    
    read -p "Do you want to proceed with deployment? (yes/no): " confirm
    
    if [ "$confirm" = "yes" ]; then
        print_step "Applying Terraform configuration..."
        $TERRAFORM_CMD apply tfplan
        
        print_success "Infrastructure deployment completed!"
        
        # Show outputs
        echo ""
        print_step "Infrastructure Details:"
        $TERRAFORM_CMD output
        
    else
        print_warning "Deployment cancelled"
        rm -f tfplan
        exit 0
    fi
    
    cd ../..
}

setup_monitoring() {
    print_step "Setting up monitoring and alerting..."
    
    # The monitoring is already included in Terraform
    print_success "Monitoring configured via Terraform"
    echo "- CloudWatch dashboards"
    echo "- Cost budgets and alerts"
    echo "- Performance monitoring"
    echo "- Auto-scaling triggers"
}

show_next_steps() {
    echo ""
    print_header
    print_success "🎉 AWS Infrastructure Deployment Complete!"
    echo ""
    
    print_step "Next Steps:"
    echo "1. 📧 Configure GitHub Actions secrets with AWS credentials"
    echo "2. 🔐 Set up database passwords and API keys"
    echo "3. 🚀 Deploy your application code"
    echo "4. 🌐 Configure domain name and SSL certificates"
    echo "5. 📊 Monitor costs and performance"
    echo ""
    
    print_step "Important Information:"
    echo "- SSH Key: ~/.ssh/academic_saas_aws"
    echo "- AWS Region: $AWS_REGION"
    echo "- Cost Budget: \$100/month with alerts"
    echo "- Free Tier: Most resources covered for 12 months"
    echo ""
    
    print_step "Access Your Infrastructure:"
    echo "- AWS Console: https://console.aws.amazon.com"
    echo "- Terraform State: S3 bucket (created automatically)"
    echo "- Monitoring: CloudWatch dashboards"
    echo ""
    
    print_warning "Security Reminders:"
    echo "- Keep your SSH private key secure"
    echo "- Rotate AWS credentials regularly"  
    echo "- Monitor cost alerts closely"
    echo "- Review security groups before production"
}

# Main execution
main() {
    print_header
    
    check_prerequisites
    setup_ssh_key
    setup_terraform_backend
    prepare_terraform_vars
    deploy_infrastructure
    setup_monitoring
    show_next_steps
}

# Run main function
main "$@"