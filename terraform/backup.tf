# =============================================================================
# Context Backup Infrastructure
# =============================================================================
# S3 bucket with Intelligent-Tiering for cost-optimized context backups
# EventBridge scheduled rule to trigger backups daily
# IAM permissions for ECS task to perform backups

# =============================================================================
# S3 Bucket for Context Backups
# =============================================================================

resource "aws_s3_bucket" "backups" {
  bucket = "${local.name_prefix}-backups-${local.account_id}"

  tags = {
    Name    = "${local.name_prefix}-backups"
    Purpose = "Context and state backups"
  }
}

resource "aws_s3_bucket_versioning" "backups" {
  bucket = aws_s3_bucket.backups.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "backups" {
  bucket = aws_s3_bucket.backups.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "backups" {
  bucket = aws_s3_bucket.backups.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Intelligent-Tiering configuration for automatic cost optimization
resource "aws_s3_bucket_intelligent_tiering_configuration" "backups" {
  bucket = aws_s3_bucket.backups.id
  name   = "EntireBucket"

  tiering {
    access_tier = "ARCHIVE_ACCESS"
    days        = 90
  }

  tiering {
    access_tier = "DEEP_ARCHIVE_ACCESS"
    days        = 180
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "backups" {
  bucket = aws_s3_bucket.backups.id

  # Daily backups - keep for 30 days, then transition to Intelligent-Tiering
  rule {
    id     = "backup-lifecycle"
    status = "Enabled"

    filter {
      prefix = "backups/context/"
    }

    transition {
      days          = 30
      storage_class = "INTELLIGENT_TIERING"
    }

    # Delete old backups after 365 days
    expiration {
      days = 365
    }

    # Clean up incomplete multipart uploads
    abort_incomplete_multipart_upload {
      days_after_initiation = 1
    }
  }

  # Current state sync - keep 7 versions
  rule {
    id     = "current-state-cleanup"
    status = "Enabled"

    filter {
      prefix = "current/"
    }

    noncurrent_version_expiration {
      noncurrent_days = 7
    }
  }
}

# =============================================================================
# EventBridge Schedule for Daily Backups
# =============================================================================

resource "aws_cloudwatch_event_rule" "backup_schedule" {
  name                = "${local.name_prefix}-backup-schedule"
  description         = "Trigger daily context backup"
  schedule_expression = "cron(0 3 * * ? *)" # 3 AM UTC daily

  tags = {
    Name = "${local.name_prefix}-backup-schedule"
  }
}

# EventBridge target - runs a backup task using the same task definition
resource "aws_cloudwatch_event_target" "backup_task" {
  rule      = aws_cloudwatch_event_rule.backup_schedule.name
  target_id = "run-backup-task"
  arn       = aws_ecs_cluster.main.arn
  role_arn  = aws_iam_role.eventbridge_ecs.arn

  ecs_target {
    task_count          = 1
    task_definition_arn = aws_ecs_task_definition.backup.arn
    launch_type         = "FARGATE"
    platform_version    = "LATEST"

    network_configuration {
      subnets          = aws_subnet.public[*].id
      security_groups  = [aws_security_group.ecs.id]
      assign_public_ip = true
    }
  }
}

# IAM role for EventBridge to run ECS tasks
resource "aws_iam_role" "eventbridge_ecs" {
  name = "${local.name_prefix}-eventbridge-ecs"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "events.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy" "eventbridge_ecs" {
  name = "${local.name_prefix}-eventbridge-ecs"
  role = aws_iam_role.eventbridge_ecs.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = "ecs:RunTask"
        Resource = aws_ecs_task_definition.backup.arn
      },
      {
        Effect = "Allow"
        Action = "iam:PassRole"
        Resource = [
          aws_iam_role.ecs_execution.arn,
          aws_iam_role.ecs_task.arn
        ]
      }
    ]
  })
}

# =============================================================================
# Backup Task Definition (lightweight task just for backups)
# =============================================================================

resource "aws_ecs_task_definition" "backup" {
  family                   = "${local.name_prefix}-backup"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = 256 # Minimal CPU for backup task
  memory                   = 512 # Minimal memory for backup task
  execution_role_arn       = aws_iam_role.ecs_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  # ARM64 for cost savings (matches main task)
  runtime_platform {
    operating_system_family = "LINUX"
    cpu_architecture        = var.use_arm64 ? "ARM64" : "X86_64"
  }

  container_definitions = jsonencode([
    {
      name      = "backup"
      image     = "amazon/aws-cli:latest"
      essential = true

      command = [
        "sh", "-c",
        <<-EOT
          echo "Starting context backup..."
          TIMESTAMP=$(date +%Y%m%d-%H%M%S)

          # Create backup archive
          cd /workspace/.claude
          tar -czf /tmp/context-backup-$TIMESTAMP.tar.gz context/

          # Upload to S3 with intelligent tiering
          aws s3 cp /tmp/context-backup-$TIMESTAMP.tar.gz \
            s3://${aws_s3_bucket.backups.id}/backups/context/$TIMESTAMP.tar.gz \
            --storage-class INTELLIGENT_TIERING

          # Sync current state
          aws s3 sync /workspace/.claude/context/ \
            s3://${aws_s3_bucket.backups.id}/current/context/ \
            --storage-class INTELLIGENT_TIERING \
            --delete

          echo "Backup completed: $TIMESTAMP"
        EOT
      ]

      mountPoints = [
        {
          sourceVolume  = "workspace"
          containerPath = "/workspace"
          readOnly      = true
        }
      ]

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.main.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "backup"
        }
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

  tags = {
    Name = "${local.name_prefix}-backup"
  }
}

# =============================================================================
# Update ECS Task IAM Policy for Backup Operations
# =============================================================================

resource "aws_iam_role_policy" "ecs_task_backup" {
  name = "${local.name_prefix}-backup-policy"
  role = aws_iam_role.ecs_task.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "BackupBucketList"
        Effect = "Allow"
        Action = [
          "s3:ListBucket"
        ]
        Resource = aws_s3_bucket.backups.arn
      },
      {
        Sid    = "BackupBucketAccess"
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject"
        ]
        Resource = "${aws_s3_bucket.backups.arn}/*"
      }
    ]
  })
}
