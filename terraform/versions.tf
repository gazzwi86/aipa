terraform {
  required_version = ">= 1.10.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # S3 backend for state storage
  # Native S3 locking (use_lockfile) requires Terraform 1.10+
  # No DynamoDB needed - uses S3 Conditional Writes
  backend "s3" {
    bucket       = "aipa-terraform-state-934536640135"
    key          = "aipa/terraform.tfstate"
    region       = "ap-southeast-2"
    encrypt      = true
    use_lockfile = true # Native S3 locking, no DynamoDB required
  }
}

provider "aws" {
  region  = var.aws_region
  profile = var.aws_profile

  default_tags {
    tags = {
      Project     = "aipa"
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  }
}
