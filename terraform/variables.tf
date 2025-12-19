variable "aws_region" {
  description = "AWS region for resources"
  type        = string
  default     = "ap-southeast-2"
}

variable "aws_profile" {
  description = "AWS CLI profile to use"
  type        = string
  default     = "gazzwi86"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "production"
}

variable "project_name" {
  description = "Project name for resource naming"
  type        = string
  default     = "aipa"
}

variable "agent_name" {
  description = "Name of the AI agent"
  type        = string
  default     = "Blu"
}

# ECS Configuration
variable "ecs_cpu" {
  description = "CPU units for Fargate task (256 = 0.25 vCPU)"
  type        = number
  default     = 512 # 0.5 vCPU
}

variable "ecs_memory" {
  description = "Memory in MB for Fargate task"
  type        = number
  default     = 1024 # 1 GB
}

variable "use_fargate_spot" {
  description = "Use Fargate Spot for cost savings (70% cheaper but can be interrupted)"
  type        = bool
  default     = true
}

variable "use_arm64" {
  description = "Use ARM64 (Graviton) for 20% cost savings"
  type        = bool
  default     = true
}

variable "idle_timeout_minutes" {
  description = "Minutes of inactivity before auto-shutdown (0 to disable)"
  type        = number
  default     = 30
}

variable "start_on_deploy" {
  description = "Start the service immediately after deploy (false = on-demand only)"
  type        = bool
  default     = false
}

# Networking
variable "vpc_cidr" {
  description = "CIDR block for VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "public_subnet_cidrs" {
  description = "CIDR blocks for public subnets"
  type        = list(string)
  default     = ["10.0.1.0/24", "10.0.2.0/24"]
}

# Domain (optional)
variable "domain_name" {
  description = "Domain name for API (optional, uses API Gateway URL if not set)"
  type        = string
  default     = ""
}

# GitHub
variable "github_repo" {
  description = "GitHub repository for the project"
  type        = string
  default     = "gazzwi86/aipa"
}

# Allowed Telegram Chat ID
variable "telegram_chat_id" {
  description = "Telegram chat ID allowed to interact with the bot"
  type        = string
  default     = ""
  sensitive   = true
}
