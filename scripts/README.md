# Deployment Scripts

This directory contains scripts for building, deploying, and diagnosing the Replit application.

## 📋 Scripts Overview

### 🔨 replit_build.sh
**Purpose:** Build script for Replit deployment

**When it runs:** Automatically during Replit deployment (defined in `.replit`)

**What it does:**
- ✅ Verifies Python version (3.11+)
- ✅ Checks pip availability and configuration
- ✅ Resolves pip `--user` flag conflicts
- ✅ Installs all dependencies from `requirements.txt`
- ✅ Verifies package imports
- ✅ Creates necessary directories
- ✅ Logs everything to `deployment_logs/`

**Manual usage:**
```bash
bash scripts/replit_build.sh
```

**Exit codes:**
- `0` - Success
- `1` - Build failed (check logs)

---

### 🏥 runtime_health_check.sh
**Purpose:** Runtime health checks when server starts

**When it runs:** Automatically before server starts (defined in `.replit`)

**What it does:**
- ✅ Verifies Python modules can be imported
- ✅ Checks project files exist
- ✅ Verifies data directory is accessible
- ✅ Checks environment variables
- ✅ Tests custom module imports
- ✅ Logs results to `deployment_logs/`

**Manual usage:**
```bash
bash scripts/runtime_health_check.sh
```

**Exit codes:**
- `0` - All checks passed, ready to start
- `1` - Health check failed (see logs)

---

### 🔍 diagnose.sh
**Purpose:** Interactive diagnostic tool for troubleshooting

**When to run:** Before deployment or when debugging issues

**What it does:**
- ✅ Checks git branch
- ✅ Verifies scripts are executable
- ✅ Validates `.replit` configuration
- ✅ Checks project structure
- ✅ Verifies environment variables
- ✅ Reviews recent build logs
- ✅ Provides actionable recommendations

**Usage:**
```bash
bash scripts/diagnose.sh
```

**Output:** Color-coded status report with ✅/❌/⚠️ indicators

---

## 🚀 Quick Start

### For First Deployment:

```bash
# 1. Run diagnostic to check everything
bash scripts/diagnose.sh

# 2. If all checks pass, test build locally
bash scripts/replit_build.sh

# 3. Test runtime checks
bash scripts/runtime_health_check.sh

# 4. If both pass, deploy via Replit UI
```

### For Troubleshooting:

```bash
# Run diagnostic first
bash scripts/diagnose.sh

# Check build logs
ls -lt deployment_logs/build_*.log | head -1 | xargs cat

# Check runtime logs
ls -lt deployment_logs/runtime_*.log | head -1 | xargs cat

# Search for errors
grep -i error deployment_logs/*.log | tail -20
```

---

## 📁 Log Files

All scripts write to `deployment_logs/`:

- `build_YYYYMMDD_HHMMSS.log` - Full build output
- `health_check_YYYYMMDD_HHMMSS.log` - Build-time health checks
- `runtime_YYYYMMDD_HHMMSS.log` - Runtime health checks
- `last_successful_build.txt` - Last successful build info

See `deployment_logs/README.md` for detailed log documentation.

---

## 🔧 Script Maintenance

### Making Scripts Executable:

```bash
chmod +x scripts/*.sh
```

### Testing Changes:

```bash
# Test build script
bash -x scripts/replit_build.sh  # -x for debug output

# Test health check
bash -x scripts/runtime_health_check.sh

# Test diagnostic
bash scripts/diagnose.sh
```

### Adding New Scripts:

1. Create script in `scripts/` directory
2. Make it executable: `chmod +x scripts/yourscript.sh`
3. Add documentation here
4. Add to `.replit` if needed for deployment

---

## ⚙️ Environment Variables

Scripts respect these environment variables:

| Variable | Purpose | Used By |
|----------|---------|---------|
| `PIP_USER` | Set to 0 to avoid --user conflicts | build script |
| `PYTHONPATH` | Python module search path | all scripts |
| `ALPHA_VANTAGE_API_KEY` | Stock data API | health checks |
| `ANTHROPIC_API_KEY` | Claude AI API | health checks |
| `PERPLEXITY_API_KEY` | Perplexity LLM API | health checks |

---

## 🐛 Debugging

### Enable Debug Mode:

```bash
# Run with bash -x for detailed output
bash -x scripts/replit_build.sh

# Or set in script
set -x  # Add this at top of script
```

### Common Issues:

**Script not executable:**
```bash
chmod +x scripts/replit_build.sh
```

**Permission denied on logs:**
```bash
mkdir -p deployment_logs
chmod 755 deployment_logs
```

**Module import fails:**
```bash
# Check PYTHONPATH
echo $PYTHONPATH

# Try importing manually
python -c "import fastapi; print('OK')"
```

---

## 📚 Related Documentation

- **For deployment:** See `REPLIT_DEPLOY.md`
- **For Replit Agent:** See `REPLIT_AGENT_INSTRUCTIONS.md`
- **For logs:** See `deployment_logs/README.md`

---

## ✅ Best Practices

1. **Always run diagnose.sh before deploying**
2. **Check logs after failed builds**
3. **Keep scripts executable** (chmod +x)
4. **Test scripts locally before committing**
5. **Document changes in this README**

---

**Last Updated:** December 2, 2025
