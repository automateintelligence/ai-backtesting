---
name: neo4j-query
description: Execute Cypher queries against KS-001 Neo4j with results formatting
category: database
---

# Neo4j Query Tool

Execute Cypher queries against KS-001 Neo4j database with proper formatting and error handling.

## What This Does

1. Connects to Neo4j via docker exec
2. Executes Cypher query with proper authentication
3. Formats results as table or JSON
4. Shows indexes, constraints, and database info

## Prerequisites

- KS-001 Neo4j container running (`ks-neo4j`)
- NEO4J_PASSWORD configured

## Common Queries

### 1. Show All Indexes
```bash
ssh 'KS-001-jeff' << 'ENDSSH'
docker exec ks-neo4j cypher-shell -u neo4j -p $NEO4J_PASSWORD \
  "SHOW INDEXES"
ENDSSH
```

Expected indexes:
- `document_doc_id_idx` - Composite (doc_id + tenant_id)
- `document_embedding_idx` - Vector index (384 dims, cosine)
- `entity_entity_id_idx` - Composite (entity_id + tenant_id)

### 2. Count Documents by Tenant
```bash
ssh 'KS-001-jeff' << 'ENDSSH'
docker exec ks-neo4j cypher-shell -u neo4j -p $NEO4J_PASSWORD \
  "MATCH (d:Document) RETURN d.tenant_id, count(*) as doc_count ORDER BY doc_count DESC"
ENDSSH
```

### 3. Check Document Schema
```bash
ssh 'KS-001-jeff' << 'ENDSSH'
docker exec ks-neo4j cypher-shell -u neo4j -p $NEO4J_PASSWORD \
  "MATCH (d:Document) RETURN d LIMIT 1"
ENDSSH
```

Expected properties:
- doc_id, tenant_id, title, summary, embedding (384 dims)
- modality, citations, metadata, created_at, updated_at

### 4. Verify Vector Index
```bash
ssh 'KS-001-jeff' << 'ENDSSH'
docker exec ks-neo4j cypher-shell -u neo4j -p $NEO4J_PASSWORD \
  "CALL db.index.vector.queryNodes('document_embedding_idx', 5, [0.1]*384)
   YIELD node, score
   RETURN node.doc_id, node.title, score LIMIT 5"
ENDSSH
```

### 5. Check Tenant Isolation
```bash
# Verify all documents have tenant_id
ssh 'KS-001-jeff' << 'ENDSSH'
docker exec ks-neo4j cypher-shell -u neo4j -p $NEO4J_PASSWORD \
  "MATCH (d:Document) WHERE d.tenant_id IS NULL RETURN count(d) as orphaned_docs"
ENDSSH
```

Should return: `orphaned_docs: 0`

### 6. Database Statistics
```bash
ssh 'KS-001-jeff' << 'ENDSSH'
docker exec ks-neo4j cypher-shell -u neo4j -p $NEO4J_PASSWORD \
  "CALL db.stats.retrieve('GRAPH COUNTS') YIELD data RETURN data"
ENDSSH
```

### 7. Show Constraints
```bash
ssh 'KS-001-jeff' << 'ENDSSH'
docker exec ks-neo4j cypher-shell -u neo4j -p $NEO4J_PASSWORD \
  "SHOW CONSTRAINTS"
ENDSSH
```

### 8. Clear Test Data (Careful!)
```bash
# Delete all documents for test tenant
ssh 'KS-001-jeff' << 'ENDSSH'
docker exec ks-neo4j cypher-shell -u neo4j -p $NEO4J_PASSWORD \
  "MATCH (d:Document {tenant_id: 'test-tenant-001'}) DETACH DELETE d"
ENDSSH
```

## Custom Query Template

```bash
ssh 'KS-001-jeff' << 'ENDSSH'
docker exec ks-neo4j cypher-shell -u neo4j -p $NEO4J_PASSWORD \
  "YOUR_CYPHER_QUERY_HERE"
ENDSSH
```

## Output Formatting

### Table Format (Default)
```
+-------------+------------------+-----------+
| tenant_id   | doc_count        |           |
+-------------+------------------+-----------+
| tenant-001  | 1523             |           |
+-------------+------------------+-----------+
```

### JSON Format
```bash
docker exec ks-neo4j cypher-shell -u neo4j -p $NEO4J_PASSWORD \
  --format plain \
  "MATCH (d:Document) RETURN d LIMIT 1"
```

## Troubleshooting

**Authentication Failures:**
```bash
# Verify password
echo $NEO4J_PASSWORD

# Test connection
docker exec ks-neo4j cypher-shell -u neo4j -p $NEO4J_PASSWORD "RETURN 1"
```

**Container Not Running:**
```bash
docker ps | grep neo4j
docker logs ks-neo4j
```

**Database Not Ready:**
```bash
# Wait for healthcheck
docker inspect ks-neo4j | grep -A 5 Health
```
