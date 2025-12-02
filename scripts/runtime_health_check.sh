#!/bin/bash
# Runtime Health Check Script
# Runs when the server starts to verify everything is ready

set -e

# Configuration
LOG_DIR="deployment_logs"
RUNTIME_LOG="${LOG_DIR}/runtime_$(date +%Y%m%d_%H%M%S).log"

# Create logs directory
mkdir -p "${LOG_DIR}"

# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "${RUNTIME_LOG}"
}

log_error() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: $1" | tee -a "${RUNTIME_LOG}" >&2
}

log_success() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ✅ $1" | tee -a "${RUNTIME_LOG}"
}

log "=========================================="
log "Runtime Health Check"
log "=========================================="

# Check 1: Python modules
log "Check 1: Verifying Python modules..."
MODULES=("fastapi" "uvicorn" "APScheduler" "httpx" "pydantic" "loguru" "anthropic")

for module in "${MODULES[@]}"; do
    if python -c "import ${module,,}" 2>/dev/null; then
        log_success "${module} OK"
    else
        log_error "${module} FAILED - cannot import"
        exit 1
    fi
done

# Check 2: Project files
log "Check 2: Verifying project files..."
FILES=("src/core/server.py" "src/core/cache.py" "src/core/scheduler.py")

for file in "${FILES[@]}"; do
    if [ -f "${file}" ]; then
        log_success "${file} OK"
    else
        log_error "${file} NOT FOUND"
        exit 1
    fi
done

# Check 3: Data directory
log "Check 3: Checking data directory..."
if [ -d "data" ]; then
    log_success "data/ directory exists"
    log "Permissions: $(ls -ld data | awk '{print $1}')"
else
    log "Creating data/ directory..."
    mkdir -p data
    log_success "data/ directory created"
fi

# Check 4: Environment variables
log "Check 4: Checking environment variables..."
ENV_VARS=("ALPHA_VANTAGE_API_KEY" "ANTHROPIC_API_KEY" "PERPLEXITY_API_KEY")
ENV_COUNT=0

for var in "${ENV_VARS[@]}"; do
    if [ ! -z "${!var}" ]; then
        log_success "${var} is set"
        ((ENV_COUNT++))
    else
        log "⚠️  ${var} not set (optional)"
    fi
done

if [ ${ENV_COUNT} -gt 0 ]; then
    log_success "At least one API key configured"
else
    log "⚠️  No API keys configured - some features may not work"
fi

# Check 5: Port availability
log "Check 5: Checking if port 8080 is available..."
if lsof -Pi :8080 -sTCP:LISTEN -t >/dev/null 2>&1; then
    log "⚠️  Port 8080 is already in use (this is OK if server is running)"
else
    log_success "Port 8080 is available"
fi

# Check 6: Test imports of our modules
log "Check 6: Testing custom module imports..."
if python -c "from src.core.cache import get_cache; from src.core.scheduler import get_scheduler" 2>/dev/null; then
    log_success "Custom modules import successfully"
else
    log_error "Custom module import failed"
    log "PYTHONPATH: ${PYTHONPATH}"
    exit 1
fi

# Summary
log "=========================================="
log "✅ Runtime Health Check PASSED"
log "=========================================="
log "Log saved to: ${RUNTIME_LOG}"
log "Ready to start server!"

exit 0
