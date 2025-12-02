# Deployment Logs

This directory contains logs for debugging Replit deployments and runtime issues.

## 📁 Log Files

### Build Logs
- **Pattern:** `build_YYYYMMDD_HHMMSS.log`
- **Purpose:** Captures the entire build process including dependency installation
- **Contains:**
  - Python version check
  - pip configuration
  - Dependency installation output
  - Package verification
  - Build health checks

### Health Check Logs
- **Pattern:** `health_check_YYYYMMDD_HHMMSS.log`
- **Purpose:** Records system health during build
- **Contains:**
  - Python version details
  - pip version and configuration
  - Disk space information
  - Package verification results

### Runtime Logs
- **Pattern:** `runtime_YYYYMMDD_HHMMSS.log`
- **Purpose:** Captures runtime health checks when server starts
- **Contains:**
  - Module import verification
  - Environment variable checks
  - Port availability checks
  - Custom module import tests

### Build Success Marker
- **File:** `last_successful_build.txt`
- **Purpose:** Records the last successful build timestamp
- **Use:** Quick check to see if build succeeded

## 🔍 How to Use These Logs

### For Build Issues:
```bash
# View latest build log
ls -lt deployment_logs/build_*.log | head -1 | xargs cat

# Search for errors in build logs
grep -i error deployment_logs/build_*.log

# Check last successful build
cat deployment_logs/last_successful_build.txt
```

### For Runtime Issues:
```bash
# View latest runtime log
ls -lt deployment_logs/runtime_*.log | head -1 | xargs cat

# Check if specific module failed
grep -i "FAILED" deployment_logs/runtime_*.log
```

### For Debugging with Replit Agent:
```bash
# Show summary of recent builds
echo "=== Recent Build Status ==="
tail -20 deployment_logs/build_*.log 2>/dev/null || echo "No build logs found"

# Show what failed
echo "=== Errors Found ==="
grep -h "ERROR" deployment_logs/*.log | tail -10 || echo "No errors found"
```

## 🗑️ Log Cleanup

Logs are kept indefinitely by default. To clean up old logs:

```bash
# Remove logs older than 7 days
find deployment_logs/ -name "*.log" -mtime +7 -delete

# Keep only last 10 logs of each type
ls -t deployment_logs/build_*.log | tail -n +11 | xargs rm -f
ls -t deployment_logs/runtime_*.log | tail -n +11 | xargs rm -f
ls -t deployment_logs/health_check_*.log | tail -n +11 | xargs rm -f
```

## 📊 Log Analysis

### Check Build Success Rate:
```bash
echo "Total builds: $(ls deployment_logs/build_*.log 2>/dev/null | wc -l)"
echo "Failed builds: $(grep -l "ERROR" deployment_logs/build_*.log 2>/dev/null | wc -l)"
```

### Find Most Common Errors:
```bash
grep "ERROR" deployment_logs/*.log | sed 's/.*ERROR: //' | sort | uniq -c | sort -rn | head -5
```

### Check Package Installation Times:
```bash
grep "Dependencies installed" deployment_logs/build_*.log
```

## 🤖 For Replit Agent

If you're a Replit AI agent helping debug deployment issues, use these commands:

### Quick Diagnostic:
```bash
# Run this first to get overview
cat << 'EOF'
=== DEPLOYMENT DIAGNOSTIC ===
EOF

echo "Last successful build:"
cat deployment_logs/last_successful_build.txt 2>/dev/null || echo "No successful builds recorded"

echo -e "\nRecent errors:"
grep "ERROR" deployment_logs/*.log 2>/dev/null | tail -5 || echo "No errors found"

echo -e "\nLatest build status:"
tail -10 deployment_logs/build_*.log 2>/dev/null | tail -10 || echo "No build logs"
```

### Check Specific Issues:

**For pip conflicts:**
```bash
grep -i "conflict\|user\|target" deployment_logs/build_*.log | tail -10
```

**For import errors:**
```bash
grep -i "import\|module" deployment_logs/runtime_*.log | tail -10
```

**For dependency issues:**
```bash
grep -i "could not find\|no matching" deployment_logs/build_*.log | tail -10
```

## 📝 Log Format

All logs follow this format:
```
[YYYY-MM-DD HH:MM:SS] LEVEL: Message
```

Levels:
- `INFO` - Normal operation
- `✅` - Success markers
- `ERROR` - Failures that stop the build/runtime
- `⚠️` - Warnings (non-critical)

## 🔧 Maintenance

This directory is automatically created by build scripts. No manual setup required.

**Git Ignore:** Add `deployment_logs/*.log` to `.gitignore` to avoid committing logs.

**Size Management:** Logs can grow large. Consider implementing log rotation or cleanup in production.
