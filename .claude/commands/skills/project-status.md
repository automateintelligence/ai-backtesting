---
name: project-status
description: Quick project state summary - what's done, current phase, what's next
category: context-restoration
---

# Project Status

Get back up to speed quickly after context window reset.

## What This Does

1. Shows current git branch and recent commits (last 10)
2. Lists completed phases and their commit dates
3. Shows current phase from tasks.md
4. Lists pending tasks
5. Shows what's deployed to KS-001
6. Identifies blocking issues or incomplete work

## Workflow

### 1. Git Status
```bash
git branch -vv
git log --oneline --decorate -10
git status
```

### 2. Phase Progress
Read these files in order:
- `specs/001-backend-mcp-plan/tasks.md` - Current phase and task list
- `specs/001-backend-mcp-plan/spec.md` - User stories and acceptance criteria
- `CLAUDE.md` - Session history if it exists
- `README.md` - Current implementation status

### 3. Deployment State
```bash
# Check what's on KS-001
ssh 'KS-001-jeff' 'cd /opt/knowledgesight/backend && git log -1 --oneline'

# Compare with local main
git log -1 --oneline main
```

### 4. Test Status
```bash
# Last test run results
ls -lt tests/
cat pytest.ini
```

### 5. Recent Activity
```bash
# Files changed in last 24 hours
find . -name "*.py" -mtime -1 -type f

# Recent commits grouped by phase
git log --since="7 days ago" --oneline --all
```

## Output Summary Format

**Project:** KnowledgeSight Backend MCP Server
**Branch:** 001-backend-mcp-plan
**Last Commit:** [hash] [message]

**Completed Phases:**
- ✅ Phase 1: Project structure (7ef22b1)
- ✅ Phase 2: Core infrastructure (c6f57bd)
- ✅ Phase 3: Vector search MCP tool (0d25ca8)

**Current Phase:** Phase 4
**Progress:** 0/? tasks complete

**Deployment:**
- KS-001: commit [hash], status: [running/stopped]
- Services: Neo4j (✅), Redis (✅), MCP Server (❌ - needs restart)

**Blocking Issues:**
- [ ] .env contains plaintext passwords (security concern)
- [ ] Tests not yet run (missing testcontainers)

**Next Steps:**
1. Implement Docker secrets for password management
2. Run integration test suite
3. Deploy and verify vector search tool

## Key Files to Review

Priority order for context restoration:
1. `specs/001-backend-mcp-plan/tasks.md` - What's done, what's next
2. `DEPLOYMENT.md` - Current deployment process
3. `specs/001-backend-mcp-plan/spec.md` - User stories
4. `src/server.py` - MCP server entry point
5. `src/tools/vector_search.py` - Current tool implementation
