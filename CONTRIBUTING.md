# Contributing Guide

## Branching Strategy

### Branch Structure

```
main (production)
├── develop (integration)
├── feature/* (new features)
├── fix/* (bug fixes)
└── agents/* (agent-specific work)
```

### Branch Types

| Branch Type | Naming | Purpose | Base Branch |
|-------------|--------|---------|-------------|
| **main** | `main` | Production-ready code, deployed to Replit | - |
| **develop** | `develop` | Integration branch for next release | `main` |
| **feature** | `feature/description` | New features | `develop` |
| **fix** | `fix/description` | Bug fixes | `develop` or `main` |
| **agents** | `agents/agent-name` | Agent development | `develop` |

---

## Development Workflow

### 1. Creating a New Feature

```bash
# Start from develop
git checkout develop
git pull origin develop

# Create feature branch
git checkout -b feature/my-new-feature

# Work on your feature
# ... make changes ...

# Commit your changes
git add .
git commit -m "Add: Description of feature"

# Push to remote
git push -u origin feature/my-new-feature
```

### 2. Creating a Pull Request

1. Go to GitHub repository
2. Click "New Pull Request"
3. Base: `develop` ← Compare: `feature/my-new-feature`
4. Fill in PR template:
   - Description of changes
   - Testing done
   - Screenshots (if UI changes)
5. Wait for CI/CD checks to pass
6. Request review if needed
7. Merge when approved

### 3. Merging to Main (Production)

Only merge to `main` when:
- All tests pass ✅
- Code reviewed
- Integration tested
- Ready for production deployment

```bash
# Create PR from develop to main
Base: main ← Compare: develop
```

---

## CI/CD Pipeline

### Automated Checks on PR

When you create a PR, these checks run automatically:

1. **Tests** - All unit tests must pass
2. **Linting** - Code quality checks
3. **Integration Tests** - API endpoints tested
4. **Health Checks** - Server startup validation

### Manual Testing Checklist

Before merging to main, verify:

- [ ] All agents work correctly
- [ ] Health monitor returns valid data
- [ ] Stock monitor returns valid data
- [ ] API documentation is up-to-date
- [ ] No breaking changes to existing APIs

---

## Agent Development Workflow

### Creating a New Agent

1. **Create agent branch**
```bash
git checkout -b agents/my-agent develop
```

2. **Implement agent**
- Create `src/agents/my_agent.py`
- Inherit from `BaseAgent`
- Implement `name`, `description`, `run()` methods

3. **Add API routes**
- Add endpoints in `src/api/routes/agents.py`
- Follow existing pattern (run, status, etc.)

4. **Create GitHub workflow** (optional)
- Copy `.github/workflows/agent-template.yml`
- Customize for your agent

5. **Add tests**
- Create `tests/test_my_agent.py`
- Test agent execution
- Test API endpoints

6. **Update documentation**
- Update README.md
- Document API endpoints
- Add usage examples

7. **Create PR**
```bash
git push -u origin agents/my-agent
# Create PR: develop ← agents/my-agent
```

---

## Commit Message Format

Use clear, descriptive commit messages:

```
Type: Short description

Longer description if needed
- Bullet points for details
- What changed
- Why it changed
```

### Commit Types

- `Add:` New feature or file
- `Fix:` Bug fix
- `Update:` Modification to existing feature
- `Remove:` Deletion of code/feature
- `Refactor:` Code restructuring
- `Docs:` Documentation only
- `Test:` Adding or updating tests

### Examples

```
Add: Stock Monitor Agent for market data

- Fetches top 10 stocks via yfinance
- Includes demo data fallback
- Claude-friendly response format
```

```
Fix: Replit deployment configuration

- Use venv in /tmp for Nix compatibility
- Resolve pip install errors
```

---

## Testing Requirements

### Unit Tests

All agents must have unit tests:

```python
# tests/test_my_agent.py
import pytest
from src.agents.my_agent import my_agent

@pytest.mark.asyncio
async def test_agent_execution():
    result = await my_agent.execute()
    assert result["status"] == "success"
```

### Integration Tests

Test API endpoints:

```python
def test_agent_api_endpoint(client):
    response = client.post("/api/v1/agents/my-agent/run")
    assert response.status_code == 200
```

### Run Tests Locally

```bash
# Install test dependencies
pip install -r requirements.txt

# Run all tests
pytest tests/ -v

# Run specific test
pytest tests/test_my_agent.py -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html
```

---

## Deployment Process

### Develop → Main → Replit

1. **Merge to develop**
   - All feature branches merge here first
   - Run integration tests
   - Verify all agents work

2. **Create Release PR**
   ```bash
   # When ready for production
   git checkout main
   git pull origin main
   git merge develop
   git push origin main
   ```

3. **Deploy to Replit**
   - Replit auto-deploys from `main` branch
   - Monitor deployment logs
   - Verify health endpoints

4. **Post-Deployment Verification**
   ```bash
   # Check health
   curl https://your-repl.replit.app/health

   # Check agents
   curl https://your-repl.replit.app/api/v1/agents

   # Test each agent
   curl -X POST https://your-repl.replit.app/api/v1/agents/health-monitor/run
   curl https://your-repl.replit.app/api/v1/agents/stock-monitor/quick
   ```

---

## Rollback Process

If deployment fails:

1. **Immediate Rollback**
```bash
git checkout main
git revert HEAD
git push origin main
```

2. **Fix and Redeploy**
```bash
git checkout -b fix/deployment-issue
# Fix the issue
git commit -m "Fix: Deployment issue"
git push -u origin fix/deployment-issue
# Create PR to main
```

---

## Questions?

- Check existing agents for examples
- Review closed PRs for patterns
- Ask in GitHub Discussions
