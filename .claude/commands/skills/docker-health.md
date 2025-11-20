---
name: docker-health
description: Comprehensive health check of all Docker services on KS-001
category: deployment
---

# Docker Health Check

Comprehensive health verification for all KnowledgeSight backend services running on KS-001.

## What This Does

1. Checks all containers are running
2. Verifies Neo4j connectivity and indexes
3. Tests Redis cache connectivity
4. Validates MCP server health endpoints
5. Shows container logs if issues detected
6. Provides diagnostic summary

## Prerequisites

- SSH access to KS-001: `ssh 'KS-001-jeff'`
- Docker services deployed on KS-001
- .env file configured on server

## Health Check Sequence

### 1. Container Status
```bash
ssh 'KS-001-jeff' << 'ENDSSH'
echo "=== Docker Container Status ==="
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep ks-

# Count running containers
EXPECTED=3
RUNNING=$(docker ps --filter "name=ks-" --format "{{.Names}}" | wc -l)

if [ $RUNNING -eq $EXPECTED ]; then
  echo "✅ All $EXPECTED containers running"
else
  echo "⚠️  Expected $EXPECTED containers, found $RUNNING running"
fi
ENDSSH
```

Expected containers:
- `ks-neo4j` - Neo4j database
- `ks-redis` - Redis cache
- `ks-mcp-server` - MCP server

### 2. Neo4j Health
```bash
ssh 'KS-001-jeff' << 'ENDSSH'
echo ""
echo "=== Neo4j Health Check ==="

# Check container is healthy
NEO4J_HEALTH=$(docker inspect ks-neo4j --format='{{.State.Health.Status}}')
echo "Container health: $NEO4J_HEALTH"

# Test Cypher connection
docker exec ks-neo4j cypher-shell -u neo4j -p $NEO4J_PASSWORD "RETURN 1 as test" 2>&1 | grep -q "test"
if [ $? -eq 0 ]; then
  echo "✅ Neo4j Cypher shell responsive"
else
  echo "❌ Neo4j Cypher shell not responding"
fi

# Verify vector index exists
echo "Checking vector indexes:"
docker exec ks-neo4j cypher-shell -u neo4j -p $NEO4J_PASSWORD \
  "SHOW INDEXES WHERE name CONTAINS 'embedding'" 2>&1 | grep -q "document_embedding_idx"
if [ $? -eq 0 ]; then
  echo "✅ Vector index exists"
else
  echo "⚠️  Vector index missing - run schema initialization"
fi

# Count documents
DOC_COUNT=$(docker exec ks-neo4j cypher-shell -u neo4j -p $NEO4J_PASSWORD \
  "MATCH (d:Document) RETURN count(d) as count" 2>&1 | grep -E "^[0-9]+$" | head -1)
echo "Document count: ${DOC_COUNT:-0}"
ENDSSH
```

### 3. Redis Health
```bash
ssh 'KS-001-jeff' << 'ENDSSH'
echo ""
echo "=== Redis Health Check ==="

# Test PING
REDIS_PING=$(docker exec ks-redis redis-cli ping 2>&1)
if [ "$REDIS_PING" = "PONG" ]; then
  echo "✅ Redis responding to PING"
else
  echo "❌ Redis not responding: $REDIS_PING"
fi

# Check memory usage
REDIS_MEMORY=$(docker exec ks-redis redis-cli info memory | grep used_memory_human | cut -d: -f2 | tr -d '\r')
echo "Memory usage: $REDIS_MEMORY"

# Check key count
REDIS_KEYS=$(docker exec ks-redis redis-cli dbsize | grep -oE "[0-9]+")
echo "Cached keys: ${REDIS_KEYS:-0}"
ENDSSH
```

### 4. MCP Server Health
```bash
ssh 'KS-001-jeff' << 'ENDSSH'
echo ""
echo "=== MCP Server Health Check ==="

# Test /healthz endpoint
HEALTHZ=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/healthz)
if [ "$HEALTHZ" = "200" ]; then
  echo "✅ /api/healthz responding (HTTP $HEALTHZ)"
  curl -s http://localhost:8000/api/healthz | jq -r '.status'
else
  echo "❌ /api/healthz not responding (HTTP $HEALTHZ)"
fi

# Test /ready endpoint
READY=$(curl -s http://localhost:8000/api/ready 2>&1)
NEO4J_STATUS=$(echo $READY | jq -r '.neo4j // "unknown"' 2>/dev/null)
REDIS_STATUS=$(echo $READY | jq -r '.redis // "unknown"' 2>/dev/null)

echo "Dependencies:"
echo "  - Neo4j: $NEO4J_STATUS"
echo "  - Redis: $REDIS_STATUS"

if [ "$NEO4J_STATUS" = "connected" ] && [ "$REDIS_STATUS" = "connected" ]; then
  echo "✅ All dependencies connected"
else
  echo "⚠️  Some dependencies not connected"
fi

# Test /metrics endpoint
METRICS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/metrics)
if [ "$METRICS" = "200" ]; then
  echo "✅ /api/metrics responding (HTTP $METRICS)"
else
  echo "⚠️  /api/metrics not responding (HTTP $METRICS)"
fi
ENDSSH
```

### 5. Network Connectivity
```bash
ssh 'KS-001-jeff' << 'ENDSSH'
echo ""
echo "=== Network Connectivity ==="

# Check ports listening
echo "Listening ports:"
netstat -tlnp 2>/dev/null | grep -E "(7474|7687|6379|8000)" | awk '{print "  - " $4 " (" $7 ")"}'

# Verify container DNS resolution
echo "Container network:"
docker network inspect neo4j-mcp_default 2>/dev/null | jq -r '.[] | .Containers | to_entries[] | "  - \(.value.Name): \(.value.IPv4Address)"'
ENDSSH
```

### 6. Recent Logs Check
```bash
ssh 'KS-001-jeff' << 'ENDSSH'
echo ""
echo "=== Recent Errors in Logs ==="

# Check MCP server logs for errors (last 50 lines)
echo "MCP Server errors:"
docker logs --tail 50 ks-mcp-server 2>&1 | grep -iE "error|exception|failed|fatal" | tail -5

# Check Neo4j logs for errors
echo "Neo4j errors:"
docker logs --tail 50 ks-neo4j 2>&1 | grep -iE "error|exception|failed|fatal" | tail -5

# Check Redis logs for errors
echo "Redis errors:"
docker logs --tail 50 ks-redis 2>&1 | grep -iE "error|exception|failed|fatal" | tail -5
ENDSSH
```

## Quick Health Summary Output

```
=== Docker Container Status ===
ks-neo4j      Up 2 hours (healthy)   0.0.0.0:7474->7474/tcp, 0.0.0.0:7687->7687/tcp
ks-redis      Up 2 hours             0.0.0.0:6379->6379/tcp
ks-mcp-server Up 2 hours             0.0.0.0:8000->8000/tcp
✅ All 3 containers running

=== Neo4j Health Check ===
Container health: healthy
✅ Neo4j Cypher shell responsive
✅ Vector index exists
Document count: 0

=== Redis Health Check ===
✅ Redis responding to PING
Memory usage: 2.5M
Cached keys: 0

=== MCP Server Health Check ===
✅ /api/healthz responding (HTTP 200)
healthy
Dependencies:
  - Neo4j: connected
  - Redis: connected
✅ All dependencies connected
✅ /api/metrics responding (HTTP 200)

=== Network Connectivity ===
Listening ports:
  - 0.0.0.0:7474 (docker-proxy)
  - 0.0.0.0:7687 (docker-proxy)
  - 0.0.0.0:6379 (docker-proxy)
  - 0.0.0.0:8000 (docker-proxy)
Container network:
  - ks-neo4j: 172.18.0.2/16
  - ks-redis: 172.18.0.3/16
  - ks-mcp-server: 172.18.0.4/16

=== Recent Errors in Logs ===
MCP Server errors: (none)
Neo4j errors: (none)
Redis errors: (none)

✅ All systems healthy
```

## Troubleshooting Commands

### Container Not Running
```bash
# Check why container stopped
ssh 'KS-001-jeff' 'docker ps -a | grep ks-'

# View full logs
ssh 'KS-001-jeff' 'docker logs ks-mcp-server --tail 100'

# Restart specific container
ssh 'KS-001-jeff' 'docker restart ks-mcp-server'
```

### Neo4j Connection Issues
```bash
# Check Neo4j healthcheck
ssh 'KS-001-jeff' 'docker inspect ks-neo4j | jq ".[].State.Health"'

# Test connection with password from .env
ssh 'KS-001-jeff' 'cd /opt/knowledgesight/backend && source .env && docker exec ks-neo4j cypher-shell -u neo4j -p $NEO4J_PASSWORD "RETURN 1"'

# Check Neo4j logs for startup errors
ssh 'KS-001-jeff' 'docker logs ks-neo4j | tail -50'
```

### Redis Connection Issues
```bash
# Test Redis authentication (if password set)
ssh 'KS-001-jeff' 'docker exec ks-redis redis-cli -a $REDIS_PASSWORD ping'

# Check Redis configuration
ssh 'KS-001-jeff' 'docker exec ks-redis redis-cli config get maxmemory'
```

### MCP Server Not Responding
```bash
# Check if server started successfully
ssh 'KS-001-jeff' 'docker logs ks-mcp-server | grep -i "server started"'

# Check for startup errors
ssh 'KS-001-jeff' 'docker logs ks-mcp-server | grep -iE "error|exception"'

# Verify .env file exists
ssh 'KS-001-jeff' 'ls -la /opt/knowledgesight/backend/.env'

# Restart with logs
ssh 'KS-001-jeff' 'cd /opt/knowledgesight/backend/infrastructure/contabo/neo4j-mcp && docker-compose restart mcp-server && docker logs -f ks-mcp-server'
```

## Automated Health Monitoring

### Continuous Monitoring Script
```bash
# Watch health status every 5 seconds
watch -n 5 'ssh "KS-001-jeff" "curl -s http://localhost:8000/api/ready | jq ."'
```

### Alert on Failure
```bash
# Simple health check with exit code
ssh 'KS-001-jeff' << 'ENDSSH'
HEALTH=$(curl -s http://localhost:8000/api/healthz | jq -r '.status')
if [ "$HEALTH" != "healthy" ]; then
  echo "🚨 MCP Server unhealthy: $HEALTH"
  exit 1
fi
echo "✅ Healthy"
ENDSSH
```

## Performance Metrics

### Response Time Check
```bash
ssh 'KS-001-jeff' << 'ENDSSH'
echo "=== Response Times ==="
time curl -s http://localhost:8000/api/healthz > /dev/null
time docker exec ks-neo4j cypher-shell -u neo4j -p $NEO4J_PASSWORD "RETURN 1" > /dev/null 2>&1
time docker exec ks-redis redis-cli ping > /dev/null
ENDSSH
```

### Resource Usage
```bash
ssh 'KS-001-jeff' << 'ENDSSH'
echo "=== Container Resource Usage ==="
docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}" | grep ks-
ENDSSH
```
