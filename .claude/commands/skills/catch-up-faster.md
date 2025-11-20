---
name: catch-up-faster
description: Lightweight context restoration for KS backend work
category: context-restoration
---

# Catch Up (Fast Path)

Use this when the context window is fresh and you only need the essentials to resume SSD 

## 1. Snapshot Commands
```bash
git status -sb
git branch -vv
git log --oneline -5
```

## 2. Must-Read Docs (in order)
1. `specs/001-backend-mcp-plan/spec.md` → User Story 1 summary + acceptance scenarios
2. `specs/001-backend-mcp-plan/tasks.md` → Current phase / task checklist
3. `DEPLOYMENT.md` → Live runbook for KS-001 (SSE instructions)
4. `src/server.py` → FastAPI + FastMCP bootstrap (SSE mount + TLS manager)

Optional (read only if touching those areas):
- `infrastructure/contabo/neo4j-mcp/docker-compose.yml`
- `src/tools/vector_search.py`
- `src/services/neo4j_client.py`
- `src/services/auth.py`
- `src/api/ingestion.py`
- `src/ingestion/extraction.py`
- `src/ingestion/embedding.py`

## 3. Deployment Spot-Check
```bash
ssh 'KS-001-jeff' <<'ENDSSH'
cd /opt/knowledgesight/backend
git status -sb
docker ps --format 'table {{.Names}}\t{{.Status}}' | grep ks-
curl -s http://localhost:8000/api/healthz
tail -n 10 /tmp/mcp_sse.log 2>/dev/null || echo "No SSE log recorded"
ENDSSH
```

## 4. Known Facts
- **Stack:** Python 3.11, FastAPI + FastMCP (uvicorn), Neo4j 5.x, Redis 7
- **Auth:** Cloudflare KV bearer tokens (namespace **ID** must be present)
- **Transport:** SSE (`/mcp/sse` stream, `/mcp/messages/?session_id=...` POST)
- **Current Focus:** Phase 1‑3 validation, manual SSE tests, refresh Cloudflare tokens as needed
- **Open TODOs:** Re-enable TLS when certs land, automate KV token helper, wire Prometheus alerts

## 5. Debug Cheatsheet
```bash
docker logs -f ks-mcp-server
docker exec ks-neo4j cypher-shell -u neo4j -p "$NEO4J_PASSWORD" "SHOW INDEXES"
docker exec ks-redis redis-cli ping
curl -Ns -H "Accept: text/event-stream" -H "Authorization: Bearer …" http://localhost:8000/mcp/sse
```

That’s it—run the commands above, skim the four docs, and you’re ready to continue SSD with minimal token/time cost.
