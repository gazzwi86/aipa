# =============================================================================
# DynamoDB - Session Storage
# =============================================================================
# Single table design for conversation sessions
# Uses PAY_PER_REQUEST (on-demand) for free tier compatibility

resource "aws_dynamodb_table" "sessions" {
  name         = "${local.name_prefix}-sessions"
  billing_mode = "PAY_PER_REQUEST" # Free tier: 25 RCU/WCU

  hash_key  = "PK"
  range_key = "SK"

  # Primary key attributes
  attribute {
    name = "PK"
    type = "S"
  }

  attribute {
    name = "SK"
    type = "S"
  }

  # GSI1 attributes for listing sessions by date
  attribute {
    name = "GSI1PK"
    type = "S"
  }

  attribute {
    name = "GSI1SK"
    type = "S"
  }

  # Global Secondary Index for listing sessions sorted by updated date
  global_secondary_index {
    name            = "GSI1"
    hash_key        = "GSI1PK"
    range_key       = "GSI1SK"
    projection_type = "ALL"
  }

  # TTL for automatic cleanup of old messages (optional, not currently used)
  ttl {
    attribute_name = "ttl"
    enabled        = true
  }

  # Point-in-time recovery disabled for cost savings
  # Enable if you need to recover from accidental deletes
  point_in_time_recovery {
    enabled = false
  }

  tags = {
    Name = "${local.name_prefix}-sessions"
  }
}

# =============================================================================
# Schema Documentation
# =============================================================================
#
# Single Table Design:
#
# PK                | SK                | Attributes
# ------------------|-------------------|----------------------------------
# SESSION#{id}      | META              | name, created, updated, status, artifacts[]
# SESSION#{id}      | MSG#{timestamp}   | role, content, source (voice/text)
# ARTIFACT#{path}   | SESSION#{id}      | created, type, size (reverse lookup)
#
# GSI1 (for listing sessions by date):
# GSI1PK            | GSI1SK            |
# ------------------|-------------------|
# USER#default      | updated#{iso-ts}  | All session META items
#
# Access Patterns:
# 1. Get session metadata: PK=SESSION#{id}, SK=META
# 2. List session messages: PK=SESSION#{id}, SK begins_with MSG#
# 3. List all sessions: GSI1.PK=USER#default (sorted by GSI1SK desc)
# 4. Find session for artifact: PK=ARTIFACT#{path}
