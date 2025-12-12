---
layout: doc
title: Troubleshooting
nav_order: 8
---

Common issues and solutions.

## Service Issues

### "Starting Ultra..." stuck

The service isn't waking up properly.

**Check Lambda logs:**
```bash
aws logs tail /aws/lambda/aipa-wake --follow
```

**Verify ECS task can pull from ECR:**
```bash
aws ecs describe-services \
  --cluster aipa-cluster \
  --services aipa-service
```

**Check EFS mount points:**
```bash
aws efs describe-file-systems
```

**Common causes:**
- ECR image doesn't exist
- IAM role missing permissions
- Security group blocking traffic
- EFS mount target not in same subnet

### Service starts but crashes

**Check container logs:**
```bash
aws logs tail /aws/ecs/aipa --follow
```

**Common causes:**
- Missing environment variables
- Invalid OAuth token
- Memory limit too low

## Authentication Issues

### Login not working

**Verify password hash:**
```bash
# Generate new hash
python3 -c "import bcrypt; print(bcrypt.hashpw(b'YOUR_PASSWORD', bcrypt.gensalt()).decode())"
```

**Check Secrets Manager:**
```bash
aws secretsmanager get-secret-value --secret-id aipa/api-keys
```

**Verify DynamoDB table:**
```bash
aws dynamodb describe-table --table-name aipa-sessions
```

### Session expiring too quickly

**Check SESSION_SECRET is set:**
```bash
# In Secrets Manager
aws secretsmanager get-secret-value --secret-id aipa/api-keys | jq '.SecretString | fromjson | .SESSION_SECRET'
```

## Voice Issues

### Voice not working

1. **Check browser permissions**
   - Allow microphone access
   - Use HTTPS (required for WebRTC)

2. **Verify LiveKit credentials**
   ```bash
   aws secretsmanager get-secret-value --secret-id aipa/api-keys | jq '.SecretString | fromjson | .LIVEKIT_URL'
   ```

3. **Check container logs**
   ```bash
   aws logs tail /aws/ecs/aipa --follow
   ```

### Voice cutting out

**Check LiveKit connection:**
- Open browser DevTools → Network tab
- Look for WebSocket connection to LiveKit

**Common causes:**
- Network instability
- LiveKit free tier limits
- Browser tab in background (some browsers throttle)

### Poor voice quality

**Check OpenAI API key:**
```bash
# Voice uses OpenAI Whisper (STT) and TTS
aws secretsmanager get-secret-value --secret-id aipa/api-keys | jq '.SecretString | fromjson | .OPENAI_API_KEY'
```

## Infrastructure Issues

### Terraform apply fails

**Common errors:**

*"Resource already exists"*
```bash
terraform import aws_resource.name resource-id
```

*"Access denied"*
```bash
# Check AWS credentials
aws sts get-caller-identity
```

*"Quota exceeded"*
- Request limit increase in AWS console
- Or use a different region

### High AWS costs

**Check what's running:**
```bash
aws ecs list-services --cluster aipa-cluster
aws ecs describe-services --cluster aipa-cluster --services aipa-service
```

**Force shutdown:**
```bash
aws ecs update-service \
  --cluster aipa-cluster \
  --service aipa-service \
  --desired-count 0
```

**Check idle Lambda:**
```bash
aws events list-rules --name-prefix aipa
```

## Docker Issues

### Build fails

**Clear cache:**
```bash
docker system prune -a
docker compose build --no-cache
```

**Check disk space:**
```bash
docker system df
```

### Container won't start

**Check logs:**
```bash
docker compose logs -f
```

**Common causes:**
- Port already in use
- Missing .env file
- Invalid environment variables

## Claude Code Issues

### OAuth token expired

```bash
# Get new token
claude setup-token
```

### MCP server not connecting

**Debug mode:**
```bash
claude --mcp-debug
```

**Check server status:**
```
/mcp
```

### High context usage

**Check context:**
```
/context
```

**Disable unused MCP servers:**
- Edit `.mcp.json`
- Remove servers you don't need

## Getting Help

### Logs to collect

1. **Container logs**
   ```bash
   docker compose logs > container.log
   ```

2. **CloudWatch logs**
   ```bash
   aws logs get-log-events --log-group-name /aws/ecs/aipa --log-stream-name $(aws logs describe-log-streams --log-group-name /aws/ecs/aipa --order-by LastEventTime --descending --limit 1 --query 'logStreams[0].logStreamName' --output text) > cloudwatch.log
   ```

3. **Terraform state**
   ```bash
   terraform show > terraform.log
   ```

### File an issue

Open an issue on GitHub with:
- Description of the problem
- Steps to reproduce
- Relevant logs (redact secrets!)
- Environment details (OS, Docker version, etc.)

[Open an issue →](https://github.com/gazzwi86/aipa/issues/new)
