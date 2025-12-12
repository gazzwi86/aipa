# =============================================================================
# ECS Cluster & Fargate Service
# =============================================================================

resource "aws_ecs_cluster" "main" {
  name = local.name_prefix

  # Container Insights disabled for cost savings (~$0.50/month)
  # Enable if you need detailed container metrics
  setting {
    name  = "containerInsights"
    value = "disabled"
  }

  tags = {
    Name = local.name_prefix
  }
}

resource "aws_ecs_cluster_capacity_providers" "main" {
  cluster_name = aws_ecs_cluster.main.name

  capacity_providers = var.use_fargate_spot ? ["FARGATE", "FARGATE_SPOT"] : ["FARGATE"]

  default_capacity_provider_strategy {
    capacity_provider = var.use_fargate_spot ? "FARGATE_SPOT" : "FARGATE"
    weight            = 1
  }
}

# =============================================================================
# IAM Roles
# =============================================================================

# Task Execution Role (for ECS to pull images, get secrets)
resource "aws_iam_role" "ecs_execution" {
  name = "${local.name_prefix}-ecs-execution"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "ecs_execution" {
  role       = aws_iam_role.ecs_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

resource "aws_iam_role_policy" "ecs_execution_secrets" {
  name = "${local.name_prefix}-secrets"
  role = aws_iam_role.ecs_execution.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue"
        ]
        Resource = [
          aws_secretsmanager_secret.api_keys.arn
        ]
      }
    ]
  })
}

# Task Role (for the container to access AWS services)
resource "aws_iam_role" "ecs_task" {
  name = "${local.name_prefix}-ecs-task"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy" "ecs_task" {
  name = "${local.name_prefix}-task-policy"
  role = aws_iam_role.ecs_task.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      # S3 access for file sharing (scoped to our bucket only)
      {
        Sid    = "S3BucketAccess"
        Effect = "Allow"
        Action = [
          "s3:ListBucket"
        ]
        Resource = aws_s3_bucket.files.arn
      },
      {
        Sid    = "S3ObjectAccess"
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject"
        ]
        Resource = "${aws_s3_bucket.files.arn}/*"
      },
      # EFS access (scoped to our filesystem)
      {
        Sid    = "EFSAccess"
        Effect = "Allow"
        Action = [
          "elasticfilesystem:ClientMount",
          "elasticfilesystem:ClientWrite",
          "elasticfilesystem:ClientRootAccess"
        ]
        Resource = aws_efs_file_system.main.arn
        Condition = {
          Bool = {
            "elasticfilesystem:AccessedViaMountTarget" = "true"
          }
        }
      },
      # CloudWatch Logs (scoped to our log group)
      {
        Sid    = "CloudWatchLogs"
        Effect = "Allow"
        Action = [
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "${aws_cloudwatch_log_group.main.arn}:*"
      },
      # ECR GetAuthorizationToken (must be * per AWS docs)
      {
        Sid    = "ECRAuth"
        Effect = "Allow"
        Action = [
          "ecr:GetAuthorizationToken"
        ]
        Resource = "*"
      },
      # ECR repository access (scoped to our repository only)
      {
        Sid    = "ECRRepositoryAccess"
        Effect = "Allow"
        Action = [
          "ecr:BatchCheckLayerAvailability",
          "ecr:GetDownloadUrlForLayer",
          "ecr:BatchGetImage",
          "ecr:PutImage",
          "ecr:InitiateLayerUpload",
          "ecr:UploadLayerPart",
          "ecr:CompleteLayerUpload"
        ]
        Resource = aws_ecr_repository.main.arn
      },
      # ECS self-update (scoped to our service only)
      {
        Sid    = "ECSServiceUpdate"
        Effect = "Allow"
        Action = [
          "ecs:UpdateService",
          "ecs:DescribeServices"
        ]
        Resource = "arn:aws:ecs:${var.aws_region}:${local.account_id}:service/${aws_ecs_cluster.main.name}/${local.name_prefix}*"
      },
      # ECS DescribeTasks for health checks (scoped to our cluster)
      {
        Sid    = "ECSDescribeTasks"
        Effect = "Allow"
        Action = [
          "ecs:DescribeTasks"
        ]
        Resource = "arn:aws:ecs:${var.aws_region}:${local.account_id}:task/${aws_ecs_cluster.main.name}/*"
      },
      # =============================================================================
      # Read-Only AWS Access for Agent Inspection
      # Used by aws-api MCP server to inspect AWS resources and costs
      # =============================================================================
      {
        Sid    = "ComputeReadOnly"
        Effect = "Allow"
        Action = [
          # EC2
          "ec2:Describe*",
          "ec2:GetConsoleOutput",
          # ECS (broader read access)
          "ecs:Describe*",
          "ecs:List*",
          # Lambda
          "lambda:List*",
          "lambda:GetFunction",
          "lambda:GetFunctionConfiguration",
          "lambda:GetPolicy"
        ]
        Resource = "*"
      },
      {
        Sid    = "StorageReadOnly"
        Effect = "Allow"
        Action = [
          # S3 (list and metadata only, not object contents of other buckets)
          "s3:ListAllMyBuckets",
          "s3:GetBucketLocation",
          "s3:GetBucketTagging",
          "s3:GetBucketPolicy",
          "s3:GetBucketVersioning",
          "s3:GetEncryptionConfiguration",
          # EFS
          "elasticfilesystem:Describe*",
          # EBS
          "ebs:ListSnapshotBlocks"
        ]
        Resource = "*"
      },
      {
        Sid    = "NetworkingReadOnly"
        Effect = "Allow"
        Action = [
          "elasticloadbalancing:Describe*",
          "apigateway:GET",
          "route53:List*",
          "route53:Get*",
          "cloudfront:List*",
          "cloudfront:GetDistribution"
        ]
        Resource = "*"
      },
      {
        Sid    = "MonitoringReadOnly"
        Effect = "Allow"
        Action = [
          "cloudwatch:Describe*",
          "cloudwatch:GetMetricData",
          "cloudwatch:GetMetricStatistics",
          "cloudwatch:ListMetrics",
          "logs:Describe*",
          "logs:FilterLogEvents",
          "logs:GetLogEvents"
        ]
        Resource = "*"
      },
      {
        Sid    = "SecurityReadOnly"
        Effect = "Allow"
        Action = [
          # IAM (read-only, no sensitive data)
          "iam:GetRole",
          "iam:GetPolicy",
          "iam:ListRoles",
          "iam:ListPolicies",
          "iam:ListAttachedRolePolicies",
          # Secrets Manager (list only, NOT GetSecretValue)
          "secretsmanager:ListSecrets",
          "secretsmanager:DescribeSecret",
          # KMS
          "kms:ListKeys",
          "kms:DescribeKey"
        ]
        Resource = "*"
      },
      {
        Sid    = "BillingReadOnly"
        Effect = "Allow"
        Action = [
          # Cost Explorer
          "ce:GetCostAndUsage",
          "ce:GetCostForecast",
          "ce:GetDimensionValues",
          "ce:GetTags",
          # Budgets
          "budgets:ViewBudget",
          "budgets:DescribeBudgets",
          # Account (for billing info)
          "account:GetAccountInformation"
        ]
        Resource = "*"
      },
      {
        Sid    = "DatabaseReadOnly"
        Effect = "Allow"
        Action = [
          "rds:Describe*",
          "dynamodb:Describe*",
          "dynamodb:List*"
        ]
        Resource = "*"
      },
      # DynamoDB write access for session storage (scoped to our table)
      {
        Sid    = "DynamoDBSessionAccess"
        Effect = "Allow"
        Action = [
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:UpdateItem",
          "dynamodb:DeleteItem",
          "dynamodb:Query",
          "dynamodb:BatchWriteItem"
        ]
        Resource = [
          aws_dynamodb_table.sessions.arn,
          "${aws_dynamodb_table.sessions.arn}/index/*"
        ]
      }
    ]
  })
}

# =============================================================================
# ECS Task Definition
# =============================================================================

resource "aws_ecs_task_definition" "main" {
  family                   = local.name_prefix
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = var.ecs_cpu
  memory                   = var.ecs_memory
  execution_role_arn       = aws_iam_role.ecs_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  # ARM64 (Graviton) for 20% cost savings
  runtime_platform {
    operating_system_family = "LINUX"
    cpu_architecture        = var.use_arm64 ? "ARM64" : "X86_64"
  }

  container_definitions = jsonencode([
    {
      name      = "aipa"
      image     = "${aws_ecr_repository.main.repository_url}:latest"
      essential = true

      portMappings = [
        {
          containerPort = 8000
          protocol      = "tcp"
        }
      ]

      environment = [
        { name = "ENVIRONMENT", value = var.environment },
        { name = "AGENT_NAME", value = var.agent_name },
        { name = "AWS_REGION", value = var.aws_region },
        { name = "S3_BUCKET", value = aws_s3_bucket.files.id },
        { name = "AIPA_BACKUP_BUCKET", value = aws_s3_bucket.backups.id },
        { name = "DYNAMODB_SESSIONS_TABLE", value = aws_dynamodb_table.sessions.id },
        { name = "LOG_LEVEL", value = "INFO" },
        { name = "WORKSPACE", value = "/workspace" },
        { name = "STATE_DIR", value = "/state" },
        # Note: For production, consider deploying local STT/TTS as sidecars
        # or using OpenAI APIs. These URLs would need to be updated for sidecar deployment.
        # { name = "STT_BASE_URL", value = "http://localhost:8001/v1" },
        # { name = "TTS_BASE_URL", value = "http://localhost:8002/v1" },
      ]

      secrets = [
        # Claude Code CLI authentication (long-lived OAuth token)
        {
          name      = "CLAUDE_CODE_OAUTH_TOKEN"
          valueFrom = "${aws_secretsmanager_secret.api_keys.arn}:CLAUDE_CODE_OAUTH_TOKEN::"
        },
        # Web authentication
        {
          name      = "AUTH_PASSWORD_HASH"
          valueFrom = "${aws_secretsmanager_secret.api_keys.arn}:AUTH_PASSWORD_HASH::"
        },
        {
          name      = "SESSION_SECRET"
          valueFrom = "${aws_secretsmanager_secret.api_keys.arn}:SESSION_SECRET::"
        },
        # LiveKit for voice
        {
          name      = "LIVEKIT_URL"
          valueFrom = "${aws_secretsmanager_secret.api_keys.arn}:LIVEKIT_URL::"
        },
        {
          name      = "LIVEKIT_API_KEY"
          valueFrom = "${aws_secretsmanager_secret.api_keys.arn}:LIVEKIT_API_KEY::"
        },
        {
          name      = "LIVEKIT_API_SECRET"
          valueFrom = "${aws_secretsmanager_secret.api_keys.arn}:LIVEKIT_API_SECRET::"
        },
        # Optional: MCP server integrations
        {
          name      = "NOTION_API_KEY"
          valueFrom = "${aws_secretsmanager_secret.api_keys.arn}:NOTION_API_KEY::"
        },
        {
          name      = "GITHUB_TOKEN"
          valueFrom = "${aws_secretsmanager_secret.api_keys.arn}:GITHUB_TOKEN::"
        },
        # Optional: OpenAI for STT/TTS (if not using local services)
        {
          name      = "OPENAI_API_KEY"
          valueFrom = "${aws_secretsmanager_secret.api_keys.arn}:OPENAI_API_KEY::"
        }
      ]

      mountPoints = [
        {
          sourceVolume  = "workspace"
          containerPath = "/workspace"
          readOnly      = false
        },
        {
          sourceVolume  = "state"
          containerPath = "/state"
          readOnly      = false
        }
      ]

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.main.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "ecs"
        }
      }

      healthCheck = {
        command     = ["CMD-SHELL", "curl -f http://localhost:8000/health || exit 1"]
        interval    = 30
        timeout     = 10
        retries     = 3
        startPeriod = 60
      }
    }
  ])

  volume {
    name = "workspace"
    efs_volume_configuration {
      file_system_id     = aws_efs_file_system.main.id
      transit_encryption = "ENABLED"
      authorization_config {
        access_point_id = aws_efs_access_point.workspace.id
        iam             = "ENABLED"
      }
    }
  }

  volume {
    name = "state"
    efs_volume_configuration {
      file_system_id     = aws_efs_file_system.main.id
      transit_encryption = "ENABLED"
      authorization_config {
        access_point_id = aws_efs_access_point.state.id
        iam             = "ENABLED"
      }
    }
  }

  tags = {
    Name = local.name_prefix
  }
}

# Note: ECS Service is defined in api_gateway.tf with service discovery
# The service "aws_ecs_service.main_with_discovery" should be used
