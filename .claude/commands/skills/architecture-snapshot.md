---
name: architecture-snapshot
description: System architecture overview - tech stack, components, key decisions
category: context-restoration
---

# Architecture Snapshot

Comprehensive system architecture and design decisions for quick context restoration.

## What This Does

1. Summarizes tech stack and versions
2. Shows component architecture
3. Lists key design decisions and rationale
4. Shows data model and schemas
5. Identifies integration points

## Tech Stack Summary

Read these files:
- `pyproject.toml` - Python dependencies and versions
- `infrastructure/contabo/neo4j-mcp/docker-compose.yml` - Container orchestration
- `scripts/init_neo4j_schema.cypher` - Database schema

### Core Technologies
- **Python:** 3.11 with Poetry
- **MCP:** FastMCP (SSE transport)
- **Database:** Neo4j  5.26.15 (vector search, graph)
- **Cache:** Redis 7 (tenant sessions)
- **Auth:** Cloudflare KV (Phase 1 bearer tokens)
- **Deployment:** Docker Compose on Contabo VPS

## Component Architecture

```
┌─────────────────────────────────────────────────────┐
│  MCP Client (Claude Desktop, AgentCore)            │
└────────────────┬────────────────────────────────────┘
                 │ JSON-RPC 2.0 / SSE
┌────────────────▼────────────────────────────────────┐
│  FastMCP Server (src/server.py)                     │
│  ├─ Health/Metrics (src/api/)                       │
│  ├─ Authentication Middleware (src/services/auth.py)│
│  └─ MCP Tools (src/tools/)                          │
│     └─ search_similar_documents                     │
└─────┬─────────────────────────────┬─────────────────┘
      │                             │
┌─────▼─────────────────┐   ┌───────▼──────────────┐
│  Neo4j  5.26.15           │   │  Redis 7             │
│  - Documents          │   │  - Tenant cache      │
│  - Entities           │   │  - Query cache       │
│  - Vector indexes     │   └──────────────────────┘
└───────────────────────┘
      │
┌─────▼─────────────────┐
│  Cloudflare KV        │
│  - Bearer tokens      │
│  - Session metadata   │
└───────────────────────┘
```

## Key Design Decisions

Read these files for rationale:
- `specs/001-backend-mcp-plan/plan.md` - Implementation plan
- `specs/001-backend-mcp-plan/research.md` - Architecture research
- `specs/001-backend-mcp-plan/data-model.md` - Data model design

### 1. Multi-Tenant Isolation
**Decision:** Tenant ID embedded in all queries via middleware
**Rationale:** Prevent cross-tenant data leaks at database level
**Implementation:** `Neo4jClient.execute_read/write` enforces `WHERE node.tenant_id = $tenant_id`

### 2. Phase 1 Authentication
**Decision:** Cloudflare KV bearer tokens (not JWT)
**Rationale:** Simple, stateless, integrates with existing CF infrastructure
**Trade-off:** Not OAuth, requires KV latency (50-100ms)

### 3. Vector Search
**Decision:** Neo4j native vector indexes (not separate vector DB)
**Rationale:** Unified graph + vector queries, simpler ops
**Trade-off:** Limited to 384 dims, cosine only (for now)

### 4. MCP Transport
**Decision:** SSE (Server-Sent Events) not stdio
**Rationale:** Network-accessible, scalable, proper for server deployment
**Trade-off:** More complex than stdio, needs reverse proxy for HTTPS

### 5. Deployment
**Decision:** Docker Compose on Contabo VPS (not k8s)
**Rationale:** Simple, cost-effective for pre-production
**Migration Path:** Can containerize to k8s later if needed

## Data Model

### Document Node
```cypher
(:Document {
  doc_id: String,           // Unique per tenant
  tenant_id: String,        // Isolation key
  title: String,
  summary: String,
  embedding: List<Float>,   // 384 dims
  modality: String,         // text, image, audio
  citations: List<String>,
  metadata: Map,
  created_at: DateTime,
  updated_at: DateTime
})
```

### Indexes
- `document_doc_id_idx` - Composite (doc_id + tenant_id) for lookups
- `document_embedding_idx` - Vector index (384 dims, cosine, 100 candidates)
- `entity_entity_id_idx` - Composite (entity_id + tenant_id)

## Integration Points

### External Services
- **Embedding Service:** `http://localhost:9003` (TODO: not implemented yet)
- **Extraction Service:** `http://localhost:9002` (TODO: Phase 4)
- **Monitoring:** Prometheus metrics at `/api/metrics`
- **Health:** `/api/healthz`, `/api/ready`

### Future Phases
- Phase 4: Document ingestion pipeline
- Phase 5: Graph traversal MCP tool
- Phase 6: Entity resolution
- Phase 7: Multi-modal support

## Configuration Layers

1. **Environment:** `.env.production` or `.env.development`
2. **Secrets:** Docker secrets (recommended) or external files
3. **Runtime:** Environment variables in containers
4. **Application:** Pydantic Settings in `src/config.py` (TODO)

## Critical Paths

### Request Flow (Vector Search)
1. MCP client → JSON-RPC request → FastMCP server
2. Auth middleware → Cloudflare KV lookup (bearer token)
3. Tool handler → validate parameters
4. Embedding service → convert query_text to vector (or use provided embedding)
5. Neo4j → vector similarity search with tenant filter
6. Response builder → DocumentResult list + diagnostics
7. FastMCP → JSON-RPC response → MCP client

### Latency Targets
- Auth: <100ms (Cloudflare KV)
- Embedding: <500ms (external service)
- Neo4j query: <500ms (vector search)
- Total: <2s p95 (per spec.md US1)
