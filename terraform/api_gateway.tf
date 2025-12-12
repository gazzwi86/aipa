# =============================================================================
# API Gateway (HTTP API)
# =============================================================================

resource "aws_apigatewayv2_api" "main" {
  name          = "${local.name_prefix}-api"
  protocol_type = "HTTP"
  description   = "API Gateway for AIPA"

  cors_configuration {
    allow_origins = ["*"]
    allow_methods = ["GET", "POST", "OPTIONS"]
    allow_headers = ["Content-Type", "Authorization", "x-api-key"]
    max_age       = 300
  }

  tags = {
    Name = "${local.name_prefix}-api"
  }
}

# =============================================================================
# VPC Link (for private integration with ECS)
# =============================================================================

resource "aws_apigatewayv2_vpc_link" "main" {
  name               = "${local.name_prefix}-vpc-link"
  security_group_ids = [aws_security_group.ecs.id]
  subnet_ids         = aws_subnet.public[*].id

  tags = {
    Name = "${local.name_prefix}-vpc-link"
  }
}

# =============================================================================
# Service Discovery (for VPC Link integration)
# =============================================================================

resource "aws_service_discovery_private_dns_namespace" "main" {
  name        = "${local.name_prefix}.local"
  description = "Private DNS namespace for AIPA"
  vpc         = aws_vpc.main.id

  tags = {
    Name = "${local.name_prefix}-dns"
  }
}

resource "aws_service_discovery_service" "main" {
  name = "aipa"

  dns_config {
    namespace_id = aws_service_discovery_private_dns_namespace.main.id

    dns_records {
      ttl  = 10
      type = "A"
    }

    routing_policy = "MULTIVALUE"
  }

  health_check_custom_config {
    failure_threshold = 1
  }
}

# Update ECS service with service discovery
# Note: desired_count defaults to 0 for on-demand operation
# Use /wake endpoint to start the service when needed
resource "aws_ecs_service" "main_with_discovery" {
  name            = "${local.name_prefix}-with-discovery"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.main.arn
  desired_count   = var.start_on_deploy ? 1 : 0 # On-demand: starts at 0
  launch_type     = var.use_fargate_spot ? null : "FARGATE"

  dynamic "capacity_provider_strategy" {
    for_each = var.use_fargate_spot ? [1] : []
    content {
      capacity_provider = "FARGATE_SPOT"
      weight            = 1
    }
  }

  network_configuration {
    subnets          = aws_subnet.public[*].id
    security_groups  = [aws_security_group.ecs.id]
    assign_public_ip = true
  }

  service_registries {
    registry_arn = aws_service_discovery_service.main.arn
  }

  deployment_minimum_healthy_percent = 0
  deployment_maximum_percent         = 100
  force_new_deployment               = true

  depends_on = [
    aws_efs_mount_target.main,
  ]

  tags = {
    Name = local.name_prefix
  }

  lifecycle {
    ignore_changes = [task_definition]
  }
}

# =============================================================================
# API Gateway Integration
# =============================================================================

resource "aws_apigatewayv2_integration" "main" {
  api_id             = aws_apigatewayv2_api.main.id
  integration_type   = "HTTP_PROXY"
  integration_method = "ANY"
  integration_uri    = aws_service_discovery_service.main.arn
  connection_type    = "VPC_LINK"
  connection_id      = aws_apigatewayv2_vpc_link.main.id

  request_parameters = {
    "overwrite:path" = "$request.path"
  }
}

# =============================================================================
# Routes
# =============================================================================

# Health check (no auth)
resource "aws_apigatewayv2_route" "health" {
  api_id    = aws_apigatewayv2_api.main.id
  route_key = "GET /health"
  target    = "integrations/${aws_apigatewayv2_integration.main.id}"
}

# Root (no auth)
resource "aws_apigatewayv2_route" "root" {
  api_id    = aws_apigatewayv2_api.main.id
  route_key = "GET /"
  target    = "integrations/${aws_apigatewayv2_integration.main.id}"
}

# Command endpoint (auth required)
resource "aws_apigatewayv2_route" "command" {
  api_id             = aws_apigatewayv2_api.main.id
  route_key          = "POST /command"
  target             = "integrations/${aws_apigatewayv2_integration.main.id}"
  authorization_type = "NONE" # We handle auth in the app via x-api-key header
}

# Approval endpoint
resource "aws_apigatewayv2_route" "approve" {
  api_id    = aws_apigatewayv2_api.main.id
  route_key = "POST /approve"
  target    = "integrations/${aws_apigatewayv2_integration.main.id}"
}

# Catch-all for other routes
resource "aws_apigatewayv2_route" "default" {
  api_id    = aws_apigatewayv2_api.main.id
  route_key = "$default"
  target    = "integrations/${aws_apigatewayv2_integration.main.id}"
}

# =============================================================================
# Stage
# =============================================================================

resource "aws_apigatewayv2_stage" "main" {
  api_id      = aws_apigatewayv2_api.main.id
  name        = "$default"
  auto_deploy = true

  access_log_settings {
    destination_arn = aws_cloudwatch_log_group.api_gateway.arn
    format = jsonencode({
      requestId        = "$context.requestId"
      ip               = "$context.identity.sourceIp"
      requestTime      = "$context.requestTime"
      httpMethod       = "$context.httpMethod"
      routeKey         = "$context.routeKey"
      status           = "$context.status"
      responseLength   = "$context.responseLength"
      integrationError = "$context.integrationErrorMessage"
    })
  }

  default_route_settings {
    throttling_burst_limit = 100
    throttling_rate_limit  = 50
  }

  tags = {
    Name = "${local.name_prefix}-stage"
  }
}

resource "aws_cloudwatch_log_group" "api_gateway" {
  name              = "/aws/apigateway/${local.name_prefix}"
  retention_in_days = 7 # Reduced from 14 for cost savings

  tags = {
    Name = "${local.name_prefix}-api-logs"
  }
}
