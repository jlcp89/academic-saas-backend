terraform {
  backend "s3" {
    bucket         = "academic-saas-terraform-state-1752633875"
    key            = "academic-saas/terraform.tfstate"
    region         = "us-east-1"
    dynamodb_table = "academic-saas-terraform-locks"
    encrypt        = true
  }
}
