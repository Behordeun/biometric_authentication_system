# Logging System Documentation

## Overview

Robust structured logging system for quality assurance and audit trails.

## Features

- ✅ **Structured Logging**: Consistent format across all logs
- ✅ **Level-Specific Files**: Separate files for each severity level
- ✅ **Duplicate Prevention**: Automatic deduplication of log entries
- ✅ **Context Capture**: Function call stack and metadata
- ✅ **Error Tracebacks**: Full exception details with stack traces
- ✅ **Audit Trail**: Database-backed audit logs for security events
- ✅ **HTTP Request Logging**: Automatic request/response logging

## Log Levels

| Level | File | Purpose |
|-------|------|---------|
| DEBUG | `logs/debug.log` | Detailed diagnostic information |
| INFO | `logs/info.log` | General system events |
| WARNING | `logs/warning.log` | Potential issues |
| ERROR | `logs/error.log` | Serious failures |
| CRITICAL | `logs/critical.log` | System-critical failures |

## Log Format

```
================================================================================
TIMESTAMP: 2024-01-15T12:00:00.000000
LEVEL: INFO
FUNCTION: register_user
PARENT: handle_registration
--------------------------------------------------------------------------------
MESSAGE: User registration successful
CONTEXT:
user_id: 123e4567-e89b-12d3-a456-426614174000
ip_address: 192.168.1.100
action: register
resource: user
================================================================================
```

## Usage

### Basic Logging

```python
from app.core.logging import get_logger

logger = get_logger(__name__)

# Info logging
logger.info("User logged in", additional_info={
    "user_id": user.id,
    "ip_address": request.client.host
})

# Warning logging
logger.warning("Rate limit approaching", additional_info={
    "user_id": user.id,
    "requests": 95,
    "limit": 100
})

# Error logging
try:
    # Some operation
    pass
except Exception as e:
    logger.error(e, additional_info={
        "user_id": user.id,
        "operation": "credential_verification"
    })
```

### Audit Logging

```python
from app.core.audit import log_login_attempt, log_registration

# Log login attempt
await log_login_attempt(
    db=db,
    username="user@example.com",
    ip_address="192.168.1.100",
    user_agent="Mozilla/5.0...",
    success=True,
    user_id=user.id
)

# Log registration
await log_registration(
    db=db,
    user_id=user.id,
    username="user@example.com",
    ip_address="192.168.1.100",
    user_agent="Mozilla/5.0..."
)
```

### HTTP Request Logging

Automatic via middleware - logs all requests/responses:

```
Request: POST /auth/login
Response: POST /auth/login - 200 (duration: 145.23ms)
```

## Audit Events

### Event Types

- **authentication**: Login/logout events
- **user_management**: Registration, profile updates
- **credential_management**: WebAuthn credential operations
- **token_management**: Token issuance/refresh
- **security**: Security alerts and violations

### Audit Log Schema

```sql
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY,
    event_type VARCHAR NOT NULL,
    user_id UUID,
    ip_address VARCHAR,
    user_agent VARCHAR,
    resource VARCHAR,
    action VARCHAR NOT NULL,
    status VARCHAR NOT NULL,
    details JSONB,
    timestamp TIMESTAMP NOT NULL
);
```

### Querying Audit Logs

```sql
-- Failed login attempts
SELECT * FROM audit_logs
WHERE event_type = 'authentication'
AND action = 'login'
AND status = 'failure'
ORDER BY timestamp DESC;

-- User activity
SELECT * FROM audit_logs
WHERE user_id = '123e4567-e89b-12d3-a456-426614174000'
ORDER BY timestamp DESC;

-- Security events
SELECT * FROM audit_logs
WHERE event_type = 'security'
ORDER BY timestamp DESC;
```

## Log Management

### View Logs

```bash
# All logs
tail -f backend/logs/*.log

# Specific level
tail -f backend/logs/error.log

# Docker logs
docker-compose logs -f backend
```

### Clear Logs

```python
from app.core.logging import system_logger, LogLevel

# Clear all logs
system_logger.clear_logs()

# Clear specific level
system_logger.clear_logs(LogLevel.ERROR)
```

### Log Rotation

Configure log rotation in production:

```bash
# /etc/logrotate.d/auth-system
/app/logs/*.log {
    daily
    rotate 30
    compress
    delaycompress
    notifempty
    create 0640 app app
    sharedscripts
    postrotate
        docker-compose restart backend
    endscript
}
```

## Security Considerations

### Sensitive Data

Never log:
- Passwords or credentials
- Full credit card numbers
- API keys or secrets
- Personal identification numbers

### Log Access

- Restrict log file permissions: `chmod 640 logs/*.log`
- Use secure log aggregation services
- Encrypt logs at rest
- Implement log retention policies

## Monitoring & Alerts

### Key Metrics

- Failed login attempts (> 5 in 5 minutes)
- Error rate (> 1% of requests)
- Critical errors (any occurrence)
- Unusual access patterns

### Alert Examples

```python
# Monitor failed logins
failed_logins = await db.execute(
    select(AuditLog)
    .where(
        AuditLog.event_type == "authentication",
        AuditLog.action == "login",
        AuditLog.status == "failure",
        AuditLog.timestamp > datetime.utcnow() - timedelta(minutes=5)
    )
)

if len(failed_logins) > 5:
    logger.critical(
        Exception("Multiple failed login attempts detected"),
        additional_info={
            "count": len(failed_logins),
            "window": "5 minutes"
        }
    )
```

## Best Practices

1. **Log at appropriate levels**
   - DEBUG: Development only
   - INFO: Normal operations
   - WARNING: Recoverable issues
   - ERROR: Failures requiring attention
   - CRITICAL: System-threatening issues

2. **Include context**
   - User ID
   - IP address
   - Request ID
   - Resource being accessed

3. **Avoid log spam**
   - Use duplicate prevention
   - Rate limit verbose logs
   - Aggregate similar events

4. **Structured data**
   - Use `additional_info` dict
   - Keep messages concise
   - Use consistent keys

5. **Performance**
   - Log asynchronously in production
   - Use log levels to control verbosity
   - Implement log sampling for high-traffic endpoints

## Integration with Monitoring Tools

### ELK Stack

```yaml
# filebeat.yml
filebeat.inputs:
  - type: log
    paths:
      - /app/logs/*.log
    json.keys_under_root: true
    json.add_error_key: true
```

### CloudWatch

```python
import watchtower

handler = watchtower.CloudWatchLogHandler(
    log_group="/aws/auth-system",
    stream_name="backend"
)
logger.addHandler(handler)
```

### Datadog

```python
from datadog import initialize, statsd

# Track metrics
statsd.increment('auth.login.success')
statsd.increment('auth.login.failure')
```

## Troubleshooting

### Logs not appearing

1. Check directory permissions
2. Verify log directory exists
3. Check disk space
4. Review Docker volume mounts

### Performance issues

1. Reduce log level in production
2. Implement log sampling
3. Use asynchronous logging
4. Archive old logs

### Missing context

1. Ensure middleware is registered
2. Pass `additional_info` dict
3. Check function call stack

## Summary

The logging system provides comprehensive observability for:
- ✅ Quality assurance through detailed error tracking
- ✅ Security auditing via database-backed audit logs
- ✅ Performance monitoring through request timing
- ✅ Compliance through immutable audit trails
- ✅ Debugging through structured context capture
