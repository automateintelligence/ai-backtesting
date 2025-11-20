---
name: deploy-ks001
description: Deploy latest code to KS-001 server and verify all services
category: deployment
---

# Deploy to KS-001

Automated deployment workflow for KnowledgeSight backend to KS-001 Contabo VPS.

## What This Does

1. Pushes latest code to github main branch
2. SSHs to KS-001 and pulls latest code
3. Restarts Docker services
4. Verifies all services are healthy
5. Shows relevant logs if issues detected

## Prerequisites

- SSH access configured: `ssh 'KS-001-jeff'`
- Git remote named 'github' configured
- Docker Compose services already set up on KS-001

## Workflow

### Step 1: Push to GitHub
```bash
git push github main
```

### Step 2: Deploy on KS-001
```bash
ssh 'KS-001-jeff' << 'ENDSSH'
cd /opt/knowledgesight/backend
git pull github main
cd infrastructure/contabo/neo4j-mcp
docker-compose down
docker-compose up -d
sleep 10
docker ps
ENDSSH
```

### Step 3: Verify Services
```bash
# Health check
ssh 'KS-001-jeff' 'curl -s http://localhost:8000/api/healthz'

# Ready check
ssh 'KS-001-jeff' 'curl -s http://localhost:8000/api/ready'

# Neo4j check
ssh 'KS-001-jeff' 'docker exec ks-neo4j cypher-shell -u neo4j -p $NEO4J_PASSWORD "RETURN 1"'

# Redis check
ssh 'KS-001-jeff' 'docker exec ks-redis redis-cli ping'
```

### Step 4: Show Logs if Issues
```bash
ssh 'KS-001-jeff' 'docker logs --tail 50 ks-mcp-server'
```

## Expected Output

Healthy deployment shows:
- All 3 containers running (ks-neo4j, ks-redis, ks-mcp-server)
- `/api/healthz` returns `{"status":"healthy"}`
- `/api/ready` returns `{"status":"ready","neo4j":"connected","redis":"connected"}`
- Neo4j returns `1`
- Redis returns `PONG`

## Troubleshooting

If MCP server fails:
1. Check logs: `docker logs ks-mcp-server`
2. Verify .env exists and has correct credentials
3. Ensure Neo4j and Redis are healthy first
4. Check ports aren't in use: `netstat -tlnp | grep 8000`
