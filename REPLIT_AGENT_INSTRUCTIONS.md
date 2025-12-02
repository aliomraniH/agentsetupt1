# 🤖 Instructions for Replit AI Agent

This document provides clear instructions for Replit's AI agent to successfully deploy and debug this application.

---

## 🎯 Quick Deployment Fix

If you encounter deployment errors, follow these steps:

### Step 1: Understand the Build System

This project uses a **custom build script** that:
- ✅ Avoids pip `--user` flag conflicts
- ✅ Logs everything for debugging
- ✅ Performs health checks at build and runtime
- ✅ Creates persistent log files in `deployment_logs/`

### Step 2: Check the `.replit` Configuration

The `.replit` file should have:

```ini
[deployment]
build = ["bash", "scripts/replit_build.sh"]
run = ["bash", "-c", "bash scripts/runtime_health_check.sh && python -m uvicorn src.core.server:app --host 0.0.0.0 --port 8080"]
deploymentTarget = "autoscale"
```

**Key points:**
- ❌ **DO NOT use** `pip install --user` in deployment build
- ❌ **DO NOT use** `pip install --target` combined with `--user`
- ✅ **DO use** the custom build script: `scripts/replit_build.sh`

### Step 3: If Deployment Fails

**Read the logs:**
```bash
# View latest build log
ls -lt deployment_logs/build_*.log | head -1 | xargs cat

# View latest runtime log
ls -lt deployment_logs/runtime_*.log | head -1 | xargs cat

# Check for errors
grep -i error deployment_logs/*.log | tail -20
```

---

## 🔧 Common Issues & Solutions

### Issue 1: "pip install --user conflicts with --target"

**Diagnosis:**
```bash
grep -i "user\|target\|conflict" deployment_logs/build_*.log
```

**Solution:**
The build script (`scripts/replit_build.sh`) already handles this by:
1. Setting `PIP_USER=0` environment variable
2. Using `pip install --no-warn-script-location -r requirements.txt`
3. NOT using `--user` or `--target` flags

**If still failing:**
```bash
# Check if there's a pip config file interfering
cat ~/.pip/pip.conf 2>/dev/null || echo "No pip.conf found (good)"
cat ~/.config/pip/pip.conf 2>/dev/null || echo "No pip.conf found (good)"

# If found, check for [install] user=true and remove it
```

---

### Issue 2: "Module not found" at runtime

**Diagnosis:**
```bash
# Check runtime logs
cat deployment_logs/runtime_*.log | grep -i "module\|import"

# Verify packages are installed
pip list | grep -E "(fastapi|uvicorn|APScheduler|httpx|pydantic)"
```

**Solution:**
```bash
# Run build script manually to see what's happening
bash scripts/replit_build.sh

# If successful, check PYTHONPATH
echo $PYTHONPATH

# Try importing manually
python -c "import fastapi; import APScheduler; print('OK')"
```

---

### Issue 3: "Build script not found"

**Diagnosis:**
```bash
ls -la scripts/replit_build.sh
```

**Solution:**
```bash
# Make sure scripts directory exists
mkdir -p scripts

# Make scripts executable
chmod +x scripts/replit_build.sh
chmod +x scripts/runtime_health_check.sh

# Verify they exist
ls -la scripts/
```

---

### Issue 4: "Permission denied" for logs

**Diagnosis:**
```bash
ls -ld deployment_logs/
```

**Solution:**
```bash
# Create logs directory with proper permissions
mkdir -p deployment_logs
chmod 755 deployment_logs

# Verify it's writable
touch deployment_logs/test.log && rm deployment_logs/test.log && echo "OK"
```

---

## 📋 Pre-Deployment Checklist

Before deploying, verify:

```bash
# 1. Scripts exist and are executable
[ -f scripts/replit_build.sh ] && echo "✅ Build script exists" || echo "❌ Build script missing"
[ -x scripts/replit_build.sh ] && echo "✅ Build script executable" || echo "❌ Build script not executable"

# 2. requirements.txt exists
[ -f requirements.txt ] && echo "✅ requirements.txt exists" || echo "❌ requirements.txt missing"

# 3. Project structure is correct
[ -d src/core ] && echo "✅ src/core exists" || echo "❌ src/core missing"
[ -f src/core/server.py ] && echo "✅ server.py exists" || echo "❌ server.py missing"
[ -f src/core/cache.py ] && echo "✅ cache.py exists" || echo "❌ cache.py missing"
[ -f src/core/scheduler.py ] && echo "✅ scheduler.py exists" || echo "❌ scheduler.py missing"

# 4. .replit is configured correctly
grep -q "scripts/replit_build.sh" .replit && echo "✅ .replit uses build script" || echo "❌ .replit not configured"

# 5. Environment variables (optional but recommended)
[ ! -z "$ALPHA_VANTAGE_API_KEY" ] && echo "✅ ALPHA_VANTAGE_API_KEY set" || echo "⚠️  ALPHA_VANTAGE_API_KEY not set"
```

---

## 🚀 Deployment Steps

### For First-Time Deployment:

```bash
# Step 1: Pull latest code
git fetch origin
git checkout claude/optimize-api-memory-017vafomh7apzPdAvRf7G1Ew
git pull

# Step 2: Make scripts executable
chmod +x scripts/replit_build.sh
chmod +x scripts/runtime_health_check.sh

# Step 3: Test build script locally (optional)
bash scripts/replit_build.sh

# Step 4: Deploy
# Click the "Deploy" button in Replit UI, or use:
# replit deploy
```

### For Redeployment After Changes:

```bash
# Step 1: Pull latest changes
git pull

# Step 2: Clear old logs (optional)
rm -f deployment_logs/*.log

# Step 3: Redeploy
# Click "Deploy" button
```

---

## 🔍 Debugging Failed Deployments

### Step-by-Step Debugging Process:

**1. Check Latest Build Log:**
```bash
echo "=== LATEST BUILD LOG ==="
ls -lt deployment_logs/build_*.log | head -1 | xargs tail -50
```

**2. Identify the Error:**
```bash
echo "=== ERRORS FOUND ==="
grep "ERROR" deployment_logs/build_*.log | tail -10
```

**3. Check Specific Issues:**

**For pip issues:**
```bash
grep -i "pip\|install\|package" deployment_logs/build_*.log | tail -20
```

**For Python issues:**
```bash
grep -i "python\|import\|module" deployment_logs/*.log | tail -20
```

**For permission issues:**
```bash
grep -i "permission\|denied\|cannot" deployment_logs/*.log | tail -20
```

**4. Test Locally:**
```bash
# Run the build script manually
bash scripts/replit_build.sh

# If successful, try the runtime check
bash scripts/runtime_health_check.sh

# If both pass, try starting the server
python -m uvicorn src.core.server:app --host 0.0.0.0 --port 8080
```

**5. Check Environment:**
```bash
echo "=== ENVIRONMENT CHECK ==="
echo "Python: $(python --version)"
echo "pip: $(pip --version)"
echo "PYTHONPATH: $PYTHONPATH"
echo "PIP_USER: $PIP_USER"
echo "Working dir: $(pwd)"
```

---

## 📊 Understanding Build Logs

### Log File Locations:

```
deployment_logs/
├── build_YYYYMMDD_HHMMSS.log          # Full build output
├── health_check_YYYYMMDD_HHMMSS.log   # Build-time health checks
├── runtime_YYYYMMDD_HHMMSS.log        # Runtime health checks
└── last_successful_build.txt          # Timestamp of last success
```

### Log Sections to Check:

**1. Python Version Check:**
```bash
grep "Python version" deployment_logs/build_*.log | tail -1
```
Should show Python 3.11+

**2. Dependency Installation:**
```bash
grep -A 20 "Installing Python Dependencies" deployment_logs/build_*.log | tail -1
```
Should show "✅ Dependencies installed successfully"

**3. Package Verification:**
```bash
grep "is installed and importable" deployment_logs/build_*.log | tail -1
```
Should show all required packages

**4. Final Status:**
```bash
grep "Build completed" deployment_logs/build_*.log | tail -1
```
Should show "✅ Build completed successfully!"

---

## 🔐 Environment Variables

### Required for Full Functionality:

Set these in Replit Secrets:

```bash
ALPHA_VANTAGE_API_KEY=your-key-here        # Required for stock data
ANTHROPIC_API_KEY=your-key-here            # Optional for Claude agent
PERPLEXITY_API_KEY=your-key-here           # Optional for LLM fallback
```

### Verify Variables:

```bash
# In Replit Shell
echo "ALPHA_VANTAGE_API_KEY is set: $( [ ! -z "$ALPHA_VANTAGE_API_KEY" ] && echo "YES" || echo "NO" )"
echo "ANTHROPIC_API_KEY is set: $( [ ! -z "$ANTHROPIC_API_KEY" ] && echo "YES" || echo "NO" )"
echo "PERPLEXITY_API_KEY is set: $( [ ! -z "$PERPLEXITY_API_KEY" ] && echo "YES" || echo "NO" )"
```

---

## ✅ Successful Deployment Indicators

After deployment succeeds, verify:

### 1. Build Logs Show Success:
```bash
tail -1 deployment_logs/last_successful_build.txt
```

### 2. Runtime Health Check Passes:
```bash
grep "✅ Runtime Health Check PASSED" deployment_logs/runtime_*.log | tail -1
```

### 3. Server Starts:
```bash
# Check server logs for:
# ✓ Background stock cache scheduler started
# ✓ Stock cache initialized
```

### 4. Endpoints Respond:
```bash
# Test health endpoint
curl https://agentsetupt-1-aloomrani.replit.app/health

# Test cached endpoint
curl https://agentsetupt-1-aloomrani.replit.app/api/v1/cached/stats
```

---

## 🆘 Emergency Recovery

If everything fails:

### Option 1: Clean Slate

```bash
# Remove all cached/temporary files
rm -rf __pycache__ src/**/__pycache__
rm -rf *.pyc src/**/*.pyc
rm -rf .pytest_cache

# Clear pip cache
pip cache purge

# Reinstall from scratch
bash scripts/replit_build.sh
```

### Option 2: Manual Installation

```bash
# Install each package individually to identify the problem
pip install --no-warn-script-location fastapi
pip install --no-warn-script-location uvicorn
pip install --no-warn-script-location APScheduler
pip install --no-warn-script-location httpx
pip install --no-warn-script-location pydantic

# Test imports
python -c "import fastapi, uvicorn, APScheduler, httpx, pydantic; print('All OK')"
```

### Option 3: Fallback to Simple Deployment

If custom build script fails, use minimal deployment:

```ini
[deployment]
build = ["sh", "-c", "export PIP_USER=0 && pip install --no-warn-script-location -r requirements.txt"]
run = ["sh", "-c", "python -m uvicorn src.core.server:app --host 0.0.0.0 --port 8080"]
deploymentTarget = "autoscale"
```

---

## 📚 Additional Resources

- **Build script:** `scripts/replit_build.sh`
- **Runtime checks:** `scripts/runtime_health_check.sh`
- **Log documentation:** `deployment_logs/README.md`
- **Deployment guide:** `REPLIT_DEPLOY.md`
- **Full documentation:** `DEPLOYMENT_GUIDE.md`

---

## 🎯 Summary for Replit Agent

**When you see deployment errors:**

1. **Read the logs first:**
   ```bash
   cat deployment_logs/build_*.log | tail -50
   ```

2. **Identify the specific error:**
   ```bash
   grep ERROR deployment_logs/build_*.log
   ```

3. **Apply the appropriate fix from this document**

4. **Test the fix:**
   ```bash
   bash scripts/replit_build.sh
   ```

5. **Redeploy**

**Remember:**
- ✅ Use the build script, not manual pip install
- ✅ Check logs in `deployment_logs/`
- ✅ All health checks must pass
- ❌ Never use `--user` flag in deployment
- ❌ Never combine `--user` with `--target`

---

**Last Updated:** December 2, 2025
**Branch:** `claude/optimize-api-memory-017vafomh7apzPdAvRf7G1Ew`
