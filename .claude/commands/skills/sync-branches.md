---
name: sync-branches
description: Sync feature branch with main on local and github
category: git-workflow
---

# Sync Branches

Automated workflow to merge feature branch into main and push both branches to github.

## What This Does

1. Checks git status and confirms clean working directory
2. Merges feature branch into main with --no-ff (preserves history)
3. Pushes main branch to github
4. Switches back to feature branch
5. Pushes feature branch to github (if needed)
6. Verifies sync completed successfully

## Prerequisites

- Clean working directory (no uncommitted changes)
- Git remote named 'github' configured
- Feature branch and main branch exist locally

## Workflow

### Step 1: Verify Clean State
```bash
# Check current branch and status
git branch -vv
git status

# Ensure no uncommitted changes
if [[ -n $(git status -s) ]]; then
  echo "⚠️  Working directory has uncommitted changes. Commit or stash first."
  exit 1
fi
```

### Step 2: Merge Feature to Main
```bash
# Get current feature branch name
FEATURE_BRANCH=$(git branch --show-current)

# Switch to main and merge
git checkout main
git merge --no-ff $FEATURE_BRANCH -m "Merge feature branch $FEATURE_BRANCH into main

[Auto-generated merge commit]

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

### Step 3: Push to GitHub
```bash
# Push main to github
git push github main

# Switch back to feature branch
git checkout $FEATURE_BRANCH

# Push feature branch (if ahead of remote)
git push github $FEATURE_BRANCH
```

### Step 4: Verify Sync
```bash
# Show branch status
git branch -vv

# Verify main is synced
git log --oneline --graph --decorate -10

# Confirm both branches pushed
echo "✅ Sync complete:"
echo "  - main branch pushed to github"
echo "  - $FEATURE_BRANCH branch pushed to github"
echo "  - Currently on: $FEATURE_BRANCH"
```

## Expected Output

```
Switched to branch 'main'
Merge made by the 'ort' strategy.
 [files changed summary]

To https://github.com/automateintelligence/ai-backend.git
   abc1234..def5678  main -> main

Switched to branch '001-backend-mcp-plan'
Everything up-to-date

* 001-backend-mcp-plan abc1234 [github/001-backend-mcp-plan] Latest commit
  main                 def5678 Merge feature branch 001-backend-mcp-plan into main

✅ Sync complete:
  - main branch pushed to github
  - 001-backend-mcp-plan branch pushed to github
  - Currently on: 001-backend-mcp-plan
```

## Advanced Options

### Custom Merge Message
```bash
# Provide detailed merge commit message
git checkout main
git merge --no-ff $FEATURE_BRANCH -m "$(cat <<'EOF'
Merge phase 3 implementation into main

Completed:
- Vector search MCP tool
- Integration test suite
- Deployment configuration

Tested on KS-001 pre-production environment.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"
```

### Sync with Conflict Resolution
```bash
# If merge conflicts occur
git checkout main
git merge --no-ff $FEATURE_BRANCH

# If conflicts:
git status  # Shows conflicted files
# Resolve conflicts manually
git add .
git commit -m "Resolved merge conflicts"
git push github main
```

### Sync Specific Branch (Not Current)
```bash
# Merge different feature branch
FEATURE_BRANCH="feature-branch-name"
git checkout main
git merge --no-ff $FEATURE_BRANCH
git push github main
git checkout $FEATURE_BRANCH
git push github $FEATURE_BRANCH
```

## Troubleshooting

### Working Directory Not Clean
```bash
# Stash changes and retry
git stash
# Run sync-branches
git stash pop
```

### Remote Diverged
```bash
# Pull latest before merging
git checkout main
git pull github main
# Then retry merge
```

### Push Rejected (Force Push Needed)
```bash
# ⚠️  Only if absolutely necessary and coordinated with team
git push github main --force-with-lease
```

### Merge Conflicts
```bash
# Abort merge and investigate
git merge --abort

# Check what changed on main
git log $FEATURE_BRANCH..main --oneline

# Decide: rebase feature branch or resolve conflicts
```

## Safety Checks

**Before running:**
1. ✅ All work committed on feature branch
2. ✅ Tests passing on feature branch
3. ✅ No ongoing work by other developers on main

**After running:**
1. ✅ Both branches show correct commits
2. ✅ GitHub shows updated branches
3. ✅ No merge conflicts left unresolved

## Integration with CI/CD

After sync, GitHub Actions or other CI may trigger:
- Automated tests on main branch
- Build and deployment pipelines
- PR status updates (if PR exists)

Monitor these to ensure merge didn't break anything.
