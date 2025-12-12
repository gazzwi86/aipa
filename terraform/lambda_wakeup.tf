# =============================================================================
# On-Demand Wake-Up Lambda
# =============================================================================
# Lambda function that starts the ECS service on-demand and handles auto-shutdown
# after idle timeout. This saves ~80% on costs by only running when needed.

# =============================================================================
# Lambda Function
# =============================================================================

resource "aws_lambda_function" "wakeup" {
  function_name = "${local.name_prefix}-wakeup"
  role          = aws_iam_role.lambda_wakeup.arn
  handler       = "index.handler"
  runtime       = "python3.12"
  timeout       = 60
  memory_size   = 128
  architectures = ["arm64"] # Cost-optimized ARM

  filename         = data.archive_file.lambda_wakeup.output_path
  source_code_hash = data.archive_file.lambda_wakeup.output_base64sha256

  environment {
    variables = {
      ECS_CLUSTER      = aws_ecs_cluster.main.name
      ECS_SERVICE      = aws_ecs_service.main_with_discovery.name
      IDLE_TIMEOUT_MIN = var.idle_timeout_minutes
      AWS_REGION_NAME  = var.aws_region
    }
  }

  tags = {
    Name = "${local.name_prefix}-wakeup"
  }
}

# Lambda source code
data "archive_file" "lambda_wakeup" {
  type        = "zip"
  output_path = "${path.module}/lambda_wakeup.zip"

  source {
    content  = <<-PYTHON
import boto3
import json
import os
import time

ecs = boto3.client('ecs', region_name=os.environ.get('AWS_REGION_NAME', 'ap-southeast-2'))

CLUSTER = os.environ['ECS_CLUSTER']
SERVICE = os.environ['ECS_SERVICE']

def handler(event, context):
    """
    Handle wake-up, status check, and shutdown requests.

    Actions:
    - wake: Start the ECS service if not running
    - status: Check if the service is running and healthy
    - shutdown: Scale the service to 0
    """
    # Parse action from path or body
    action = 'status'

    if event.get('rawPath'):
        path = event['rawPath']
        if '/wake' in path:
            action = 'wake'
        elif '/shutdown' in path:
            action = 'shutdown'
        elif '/status' in path:
            action = 'status'
    elif event.get('action'):
        action = event['action']

    try:
        # Get current service state
        response = ecs.describe_services(cluster=CLUSTER, services=[SERVICE])

        if not response['services']:
            return error_response(404, 'Service not found')

        service = response['services'][0]
        desired_count = service['desiredCount']
        running_count = service['runningCount']

        if action == 'wake':
            return handle_wake(desired_count, running_count)
        elif action == 'shutdown':
            return handle_shutdown(desired_count)
        else:  # status
            return handle_status(desired_count, running_count)

    except Exception as e:
        return error_response(500, str(e))

def handle_wake(desired_count, running_count):
    """Start the service if not running."""
    if desired_count == 0:
        # Scale up
        ecs.update_service(
            cluster=CLUSTER,
            service=SERVICE,
            desiredCount=1
        )
        return success_response({
            'status': 'starting',
            'message': 'Service is starting. Please wait 30-60 seconds.',
            'desiredCount': 1,
            'runningCount': 0
        })
    elif running_count == 0:
        return success_response({
            'status': 'starting',
            'message': 'Service is starting. Please wait.',
            'desiredCount': desired_count,
            'runningCount': 0
        })
    else:
        return success_response({
            'status': 'running',
            'message': 'Service is already running.',
            'desiredCount': desired_count,
            'runningCount': running_count
        })

def handle_shutdown(desired_count):
    """Scale the service to 0."""
    if desired_count > 0:
        ecs.update_service(
            cluster=CLUSTER,
            service=SERVICE,
            desiredCount=0
        )
        return success_response({
            'status': 'stopping',
            'message': 'Service is shutting down.'
        })
    else:
        return success_response({
            'status': 'stopped',
            'message': 'Service is already stopped.'
        })

def handle_status(desired_count, running_count):
    """Return current service status."""
    if desired_count == 0:
        status = 'stopped'
    elif running_count == 0:
        status = 'starting'
    else:
        status = 'running'

    return success_response({
        'status': status,
        'desiredCount': desired_count,
        'runningCount': running_count
    })

def success_response(body):
    return {
        'statusCode': 200,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*'
        },
        'body': json.dumps(body)
    }

def error_response(code, message):
    return {
        'statusCode': code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*'
        },
        'body': json.dumps({'error': message})
    }
PYTHON
    filename = "index.py"
  }
}

# =============================================================================
# IAM Role for Lambda
# =============================================================================

resource "aws_iam_role" "lambda_wakeup" {
  name = "${local.name_prefix}-lambda-wakeup"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy" "lambda_wakeup" {
  name = "${local.name_prefix}-lambda-wakeup"
  role = aws_iam_role.lambda_wakeup.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "ECSServiceControl"
        Effect = "Allow"
        Action = [
          "ecs:DescribeServices",
          "ecs:UpdateService"
        ]
        Resource = [
          "arn:aws:ecs:${var.aws_region}:${local.account_id}:service/${aws_ecs_cluster.main.name}/*"
        ]
      },
      {
        Sid    = "CloudWatchLogs"
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:${var.aws_region}:${local.account_id}:*"
      }
    ]
  })
}

# =============================================================================
# API Gateway Integration for Lambda
# =============================================================================

resource "aws_apigatewayv2_integration" "lambda_wakeup" {
  api_id                 = aws_apigatewayv2_api.main.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.wakeup.invoke_arn
  payload_format_version = "2.0"
}

# Routes for wake-up endpoints
resource "aws_apigatewayv2_route" "wake" {
  api_id    = aws_apigatewayv2_api.main.id
  route_key = "GET /wake"
  target    = "integrations/${aws_apigatewayv2_integration.lambda_wakeup.id}"
}

resource "aws_apigatewayv2_route" "wake_post" {
  api_id    = aws_apigatewayv2_api.main.id
  route_key = "POST /wake"
  target    = "integrations/${aws_apigatewayv2_integration.lambda_wakeup.id}"
}

resource "aws_apigatewayv2_route" "status" {
  api_id    = aws_apigatewayv2_api.main.id
  route_key = "GET /status"
  target    = "integrations/${aws_apigatewayv2_integration.lambda_wakeup.id}"
}

resource "aws_apigatewayv2_route" "shutdown" {
  api_id    = aws_apigatewayv2_api.main.id
  route_key = "POST /shutdown"
  target    = "integrations/${aws_apigatewayv2_integration.lambda_wakeup.id}"
}

# Lambda permission for API Gateway
resource "aws_lambda_permission" "api_gateway" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.wakeup.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.main.execution_arn}/*/*"
}

# =============================================================================
# Auto-Shutdown Schedule (runs every 15 minutes during active hours)
# =============================================================================

resource "aws_cloudwatch_event_rule" "idle_check" {
  name                = "${local.name_prefix}-idle-check"
  description         = "Check for idle service and shut down if inactive"
  schedule_expression = "rate(15 minutes)"

  tags = {
    Name = "${local.name_prefix}-idle-check"
  }
}

resource "aws_cloudwatch_event_target" "idle_check" {
  rule      = aws_cloudwatch_event_rule.idle_check.name
  target_id = "check-idle"
  arn       = aws_lambda_function.idle_checker.arn

  input = jsonencode({
    action = "check_idle"
  })
}

resource "aws_lambda_permission" "eventbridge_idle" {
  statement_id  = "AllowEventBridgeInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.idle_checker.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.idle_check.arn
}

# =============================================================================
# Idle Checker Lambda (checks CloudWatch metrics for activity)
# =============================================================================

resource "aws_lambda_function" "idle_checker" {
  function_name = "${local.name_prefix}-idle-checker"
  role          = aws_iam_role.lambda_idle_checker.arn
  handler       = "index.handler"
  runtime       = "python3.12"
  timeout       = 60
  memory_size   = 128
  architectures = ["arm64"]

  filename         = data.archive_file.lambda_idle_checker.output_path
  source_code_hash = data.archive_file.lambda_idle_checker.output_base64sha256

  environment {
    variables = {
      ECS_CLUSTER      = aws_ecs_cluster.main.name
      ECS_SERVICE      = aws_ecs_service.main_with_discovery.name
      IDLE_TIMEOUT_MIN = var.idle_timeout_minutes
      AWS_REGION_NAME  = var.aws_region
      API_GATEWAY_ID   = aws_apigatewayv2_api.main.id
    }
  }

  tags = {
    Name = "${local.name_prefix}-idle-checker"
  }
}

data "archive_file" "lambda_idle_checker" {
  type        = "zip"
  output_path = "${path.module}/lambda_idle_checker.zip"

  source {
    content  = <<-PYTHON
import boto3
import os
from datetime import datetime, timedelta

ecs = boto3.client('ecs', region_name=os.environ.get('AWS_REGION_NAME', 'ap-southeast-2'))
cloudwatch = boto3.client('cloudwatch', region_name=os.environ.get('AWS_REGION_NAME', 'ap-southeast-2'))

CLUSTER = os.environ['ECS_CLUSTER']
SERVICE = os.environ['ECS_SERVICE']
IDLE_TIMEOUT = int(os.environ.get('IDLE_TIMEOUT_MIN', '30'))
API_GATEWAY_ID = os.environ['API_GATEWAY_ID']

def handler(event, context):
    """
    Check if the service has been idle and shut it down if so.
    Uses API Gateway request count as the activity metric.
    """
    try:
        # First check if service is running
        response = ecs.describe_services(cluster=CLUSTER, services=[SERVICE])
        if not response['services']:
            return {'status': 'service_not_found'}

        service = response['services'][0]
        if service['desiredCount'] == 0:
            return {'status': 'already_stopped'}

        if service['runningCount'] == 0:
            return {'status': 'starting_up'}

        # Check API Gateway metrics for recent activity
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(minutes=IDLE_TIMEOUT)

        response = cloudwatch.get_metric_statistics(
            Namespace='AWS/ApiGateway',
            MetricName='Count',
            Dimensions=[
                {'Name': 'ApiId', 'Value': API_GATEWAY_ID}
            ],
            StartTime=start_time,
            EndTime=end_time,
            Period=IDLE_TIMEOUT * 60,  # Entire window as one period
            Statistics=['Sum']
        )

        # Get total request count in the idle window
        total_requests = 0
        for datapoint in response.get('Datapoints', []):
            total_requests += datapoint.get('Sum', 0)

        # Exclude wake/status/shutdown calls (they shouldn't count as activity)
        # We'll be conservative and require at least 5 real requests
        if total_requests < 5:
            print(f"Service idle for {IDLE_TIMEOUT} minutes ({total_requests} requests). Shutting down.")
            ecs.update_service(
                cluster=CLUSTER,
                service=SERVICE,
                desiredCount=0
            )
            return {
                'status': 'shutdown',
                'reason': f'Idle for {IDLE_TIMEOUT} minutes',
                'requests': total_requests
            }

        return {
            'status': 'active',
            'requests': total_requests
        }

    except Exception as e:
        print(f"Error checking idle status: {e}")
        return {'status': 'error', 'message': str(e)}
PYTHON
    filename = "index.py"
  }
}

resource "aws_iam_role" "lambda_idle_checker" {
  name = "${local.name_prefix}-lambda-idle-checker"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy" "lambda_idle_checker" {
  name = "${local.name_prefix}-lambda-idle-checker"
  role = aws_iam_role.lambda_idle_checker.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "ECSServiceControl"
        Effect = "Allow"
        Action = [
          "ecs:DescribeServices",
          "ecs:UpdateService"
        ]
        Resource = [
          "arn:aws:ecs:${var.aws_region}:${local.account_id}:service/${aws_ecs_cluster.main.name}/*"
        ]
      },
      {
        Sid    = "CloudWatchMetrics"
        Effect = "Allow"
        Action = [
          "cloudwatch:GetMetricStatistics"
        ]
        Resource = "*"
      },
      {
        Sid    = "CloudWatchLogs"
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:${var.aws_region}:${local.account_id}:*"
      }
    ]
  })
}

# =============================================================================
# Output
# =============================================================================

output "wakeup_endpoint" {
  description = "Endpoint to wake up the service"
  value       = "${aws_apigatewayv2_stage.main.invoke_url}/wake"
}

output "status_endpoint" {
  description = "Endpoint to check service status"
  value       = "${aws_apigatewayv2_stage.main.invoke_url}/status"
}
