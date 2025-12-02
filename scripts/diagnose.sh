#!/bin/bash
# Quick Diagnostic Script for Deployment Issues
# Run this to check if everything is ready for deployment

echo "=========================================="
echo "🔍 Replit Deployment Diagnostic"
echo "=========================================="
echo ""

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

success() {
    echo -e "${GREEN}✅ $1${NC}"
}

error() {
    echo -e "${RED}❌ $1${NC}"
}

warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

# Check 1: Git branch
echo "1. Checking git branch..."
CURRENT_BRANCH=$(git branch --show-current)
if [ "$CURRENT_BRANCH" = "claude/optimize-api-memory-017vafomh7apzPdAvRf7G1Ew" ]; then
    success "On correct branch: $CURRENT_BRANCH"
else
    warning "On branch: $CURRENT_BRANCH (expected: claude/optimize-api-memory-017vafomh7apzPdAvRf7G1Ew)"
fi
echo ""

# Check 2: Scripts exist and are executable
echo "2. Checking deployment scripts..."
if [ -f scripts/replit_build.sh ] && [ -x scripts/replit_build.sh ]; then
    success "Build script exists and is executable"
else
    error "Build script missing or not executable"
    echo "   Run: chmod +x scripts/replit_build.sh"
fi

if [ -f scripts/runtime_health_check.sh ] && [ -x scripts/runtime_health_check.sh ]; then
    success "Runtime health check script exists and is executable"
else
    error "Runtime health check script missing or not executable"
    echo "   Run: chmod +x scripts/runtime_health_check.sh"
fi
echo ""

# Check 3: .replit configuration
echo "3. Checking .replit configuration..."
if grep -q "scripts/replit_build.sh" .replit; then
    success ".replit uses custom build script"
else
    error ".replit not configured correctly"
    echo "   Expected: build = [\"bash\", \"scripts/replit_build.sh\"]"
fi

if grep -q -- "--user" .replit; then
    error ".replit contains --user flag (will cause conflicts)"
    echo "   Remove --user from deployment build command"
else
    success "No --user flag conflicts in .replit"
fi
echo ""

# Check 4: requirements.txt
echo "4. Checking requirements.txt..."
if [ -f requirements.txt ]; then
    success "requirements.txt exists"
    if grep -q "APScheduler" requirements.txt; then
        success "APScheduler listed in requirements.txt"
    else
        error "APScheduler not in requirements.txt"
    fi
else
    error "requirements.txt not found"
fi
echo ""

# Check 5: Project structure
echo "5. Checking project structure..."
REQUIRED_DIRS=("src" "src/core" "src/agents" "src/api" "src/api/routes")
for dir in "${REQUIRED_DIRS[@]}"; do
    if [ -d "$dir" ]; then
        success "$dir/ exists"
    else
        error "$dir/ not found"
    fi
done
echo ""

# Check 6: Critical files
echo "6. Checking critical files..."
CRITICAL_FILES=("src/core/server.py" "src/core/cache.py" "src/core/scheduler.py" "src/api/routes/cached.py")
for file in "${CRITICAL_FILES[@]}"; do
    if [ -f "$file" ]; then
        success "$file exists"
    else
        error "$file not found"
    fi
done
echo ""

# Check 7: Python and pip
echo "7. Checking Python environment..."
if command -v python &> /dev/null; then
    PYTHON_VERSION=$(python --version 2>&1)
    success "Python found: $PYTHON_VERSION"

    if python -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)"; then
        success "Python version is 3.11+"
    else
        warning "Python version may be too old (need 3.11+)"
    fi
else
    error "Python not found"
fi

if command -v pip &> /dev/null; then
    PIP_VERSION=$(pip --version 2>&1)
    success "pip found: $PIP_VERSION"
else
    error "pip not found"
fi
echo ""

# Check 8: Environment variables
echo "8. Checking environment variables..."
if [ ! -z "$ALPHA_VANTAGE_API_KEY" ]; then
    success "ALPHA_VANTAGE_API_KEY is set"
else
    warning "ALPHA_VANTAGE_API_KEY not set (stock data won't refresh)"
fi

if [ ! -z "$ANTHROPIC_API_KEY" ]; then
    success "ANTHROPIC_API_KEY is set"
else
    warning "ANTHROPIC_API_KEY not set (Claude agent won't work)"
fi

if [ ! -z "$PERPLEXITY_API_KEY" ]; then
    success "PERPLEXITY_API_KEY is set"
else
    warning "PERPLEXITY_API_KEY not set (LLM fallback won't work)"
fi
echo ""

# Check 9: Logs directory
echo "9. Checking logs directory..."
if [ -d deployment_logs ]; then
    success "deployment_logs/ directory exists"
    LOG_COUNT=$(ls deployment_logs/*.log 2>/dev/null | wc -l)
    if [ $LOG_COUNT -gt 0 ]; then
        echo "   Found $LOG_COUNT log files"
    fi
else
    warning "deployment_logs/ directory doesn't exist yet (will be created on build)"
fi
echo ""

# Check 10: data directory
echo "10. Checking data directory..."
if [ -d data ]; then
    success "data/ directory exists"
    if [ -f data/stock_cache.db ]; then
        DB_SIZE=$(du -h data/stock_cache.db | cut -f1)
        echo "   Cache database exists (size: $DB_SIZE)"
    fi
else
    warning "data/ directory doesn't exist yet (will be created on first run)"
fi
echo ""

# Check 11: Recent logs
echo "11. Checking recent deployment status..."
if [ -f deployment_logs/last_successful_build.txt ]; then
    success "Found last successful build record:"
    cat deployment_logs/last_successful_build.txt | sed 's/^/   /'
else
    warning "No successful build recorded yet"
fi

if ls deployment_logs/build_*.log &>/dev/null; then
    LATEST_BUILD=$(ls -t deployment_logs/build_*.log | head -1)
    echo "   Latest build log: $LATEST_BUILD"

    if grep -q "Build completed successfully" "$LATEST_BUILD"; then
        success "Last build was successful"
    else
        error "Last build had errors"
        echo "   Check: cat $LATEST_BUILD"
    fi
fi
echo ""

# Summary
echo "=========================================="
echo "📊 Diagnostic Summary"
echo "=========================================="

# Count issues
ERROR_COUNT=0
WARNING_COUNT=0

# Recheck critical items
[ ! -f scripts/replit_build.sh ] && ((ERROR_COUNT++))
[ ! -x scripts/replit_build.sh ] && ((ERROR_COUNT++))
[ ! -f requirements.txt ] && ((ERROR_COUNT++))
[ ! -d src/core ] && ((ERROR_COUNT++))
[ ! -f src/core/server.py ] && ((ERROR_COUNT++))
grep -q -- "--user" .replit && ((ERROR_COUNT++))

[ -z "$ALPHA_VANTAGE_API_KEY" ] && ((WARNING_COUNT++))

if [ $ERROR_COUNT -eq 0 ]; then
    success "No critical errors found!"
    echo ""
    echo "✅ Ready to deploy!"
    echo ""
    echo "Next steps:"
    echo "  1. Click the 'Deploy' button in Replit"
    echo "  2. Monitor deployment_logs/build_*.log for progress"
    echo "  3. Test endpoints after deployment succeeds"
else
    error "Found $ERROR_COUNT critical error(s)"
    echo ""
    echo "❌ Fix errors before deploying"
    echo ""
    echo "See issues above for details"
fi

if [ $WARNING_COUNT -gt 0 ]; then
    warning "Found $WARNING_COUNT warning(s) (non-critical)"
fi

echo ""
echo "=========================================="
echo "For detailed instructions, see:"
echo "  - REPLIT_AGENT_INSTRUCTIONS.md"
echo "  - REPLIT_DEPLOY.md"
echo "=========================================="
