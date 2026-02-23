# Agent System Monitoring Configuration

## Prometheus Metrics

```yaml
# prometheus.yml - agent scrape config
scrape_configs:
  - job_name: 'fork-agent'
    static_configs:
      - targets: ['localhost:9090']
    metrics_path: '/metrics'
```

## Key Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `agent_status` | Gauge | 0=pending, 1=starting, 2=healthy, 3=unhealthy, 4=terminating, 5=terminated, 6=failed |
| `agent_errors_total` | Counter | Total errors for agent |
| `agent_restarts_total` | Counter | Agent restart count |
| `circuit_breaker_state` | Gauge | 0=closed, 1=open, 2=half_open |
| `ipc_messages_sent_total` | Counter | Messages sent |
| `ipc_messages_failed_total` | Counter | Failed message deliveries |
| `ipc_queue_size` | Gauge | Current queue size |
| `dlq_size` | Gauge | Dead letter queue size |

## Alert Rules

```yaml
groups:
  - name: agent_alerts
    rules:
      - alert: AgentFailed
        expr: agent_status == 6
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Agent {{ $labels.name }} failed"

      - alert: CircuitBreakerOpen
        expr: circuit_breaker_state == 1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Circuit breaker open for {{ $labels.agent }}"

      - alert: HighErrorRate
        expr: rate(agent_errors_total[5m]) > 10
        for: 2m
        labels:
          severity: warning

      - alert: DeadLetterQueueFull
        expr: dlq_size > 900
        for: 1m
        labels:
          severity: warning
        annotations:
          summary: "DLQ at {{ $value }}% capacity"
```

## Health Check Endpoint

```python
# /health endpoint response
{
  "status": "healthy",
  "agents": {
    "total": 5,
    "healthy": 4,
    "unhealthy": 1,
    "failed": 0
  },
  "circuit_breakers": {
    "closed": 4,
    "open": 1,
    "half_open": 0
  },
  "ipc": {
    "messages_pending": 12,
    "dlq_size": 5
  }
}
```
