---
name: test-mcp-tool
description: Test MCP tools with proper JSON-RPC formatting and authentication
category: testing
---

# Test MCP Tool

Execute MCP tool calls against KS-001 with proper JSON-RPC formatting and bearer token authentication.

## What This Does

1. Verifies Cloudflare KV test token exists
2. Formats JSON-RPC 2.0 request payload
3. Executes curl with proper headers
4. Parses and displays response
5. Shows diagnostics (db_ms, total_ms, result count)

## Prerequisites

- KS-001 MCP server running
- Cloudflare KV test token created (key: `test-tenant-001:test-session-001`)

## Tool Definitions

### search_similar_documents

**Parameters:**
- `query_text` (string, optional): Natural language query
- `embedding` (array[float], optional): 384-dim vector
- `top_k` (int, default 5): Number of results (1-10)
- `include_metadata` (bool, default true): Include title, summary, citations

**Example Request:**
```bash
curl -X POST http://localhost:8000/mcp/tools/call \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer test-tenant-001:test-session-001" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
      "name": "search_similar_documents",
      "arguments": {
        "query_text": "What are our Q4 revenue projections?",
        "top_k": 5,
        "include_metadata": true
      }
    },
    "id": 1
  }'
```

**Expected Response:**
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "documents": [
      {
        "doc_id": "doc-123",
        "title": "Q4 Financial Report",
        "summary": "Revenue projections...",
        "score": 0.87,
        "modality": "text",
        "citations": [],
        "metadata": {}
      }
    ],
    "diagnostics": {
      "db_ms": 145.2,
      "total_ms": 198.5,
      "retries": 0,
      "degraded": false,
      "cache_hit": false,
      "truncated": false,
      "warnings": []
    }
  }
}
```

## Common Test Scenarios

### 1. Basic Vector Search
```bash
ssh 'KS-001-jeff' << 'ENDSSH'
curl -X POST http://localhost:8000/mcp/tools/call \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer test-tenant-001:test-session-001" \
  -d '{"jsonrpc":"2.0","method":"tools/call","params":{"name":"search_similar_documents","arguments":{"query_text":"test query","top_k":3}},"id":1}' | jq
ENDSSH
```

### 2. Zero Results Test
```bash
# Query empty corpus - should return zero results with diagnostic warning
```

### 3. Invalid Auth Test
```bash
# Test with invalid token - should return 401
curl -X POST http://localhost:8000/mcp/tools/call \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer invalid-token" \
  -d '{"jsonrpc":"2.0","method":"tools/call","params":{"name":"search_similar_documents","arguments":{"query_text":"test"}},"id":1}'
```

### 4. Performance Test
```bash
# Verify <2s p95 latency - check diagnostics.total_ms
```

## Interpreting Results

**Success Indicators:**
- HTTP 200 status
- `result` field present (not `error`)
- `diagnostics.db_ms < 500` (good performance)
- `diagnostics.total_ms < 2000` (meets SLA)

**Common Errors:**
- 401: Invalid/expired bearer token
- 503: Neo4j unavailable
- 400: Missing required parameters
- 500: Internal server error (check logs)

## Creating Test KV Token

If test token doesn't exist:
```bash
curl -X PUT \
  "https://api.cloudflare.com/client/v4/accounts/$CF_ACCOUNT_ID/storage/kv/namespaces/$CF_KV_NAMESPACE_ID/values/test-tenant-001:test-session-001" \
  -H "Authorization: Bearer $CF_API_TOKEN" \
  -H "Content-Type: application/json" \
  --data '{"tenant_id":"test-tenant-001","user_id":"test-user-001","permissions":["read","write"],"session_id":"test-session-001","expires_at":"2025-11-11T00:00:00Z","region":"us-west","plan_tier":"standard"}'
```
