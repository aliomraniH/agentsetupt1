#!/bin/bash
# Replit Deployment Build Script with Health Checks
# Logs everything to deployment_logs/ for debugging

set -e  # Exit on error

# Configuration
LOG_DIR="deployment_logs"
BUILD_LOG="${LOG_DIR}/build_$(date +%Y%m%d_%H%M%S).log"
HEALTH_LOG="${LOG_DIR}/health_check_$(date +%Y%m%d_%H%M%S).log"

# Create logs directory
mkdir -p "${LOG_DIR}"

# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "${BUILD_LOG}"
}

log_error() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: $1" | tee -a "${BUILD_LOG}" >&2
}

log_success() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ✅ $1" | tee -a "${BUILD_LOG}"
}

# Start build
log "=========================================="
log "Starting Replit Deployment Build"
log "=========================================="

# Health Check 1: Python version
log "Health Check 1: Checking Python version..."
PYTHON_VERSION=$(python --version 2>&1 | tee -a "${HEALTH_LOG}")
log "Python version: ${PYTHON_VERSION}"

if python -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)"; then
    log_success "Python version OK (3.11+)"
else
    log_error "Python version too old (need 3.11+)"
    exit 1
fi

# Health Check 2: pip availability
log "Health Check 2: Checking pip..."
PIP_VERSION=$(pip --version 2>&1 | tee -a "${HEALTH_LOG}")
log "pip version: ${PIP_VERSION}"

if command -v pip &> /dev/null; then
    log_success "pip is available"
else
    log_error "pip not found"
    exit 1
fi

# Health Check 3: Check for pip config conflicts
log "Health Check 3: Checking pip configuration..."
log "Current pip config:"
pip config list 2>&1 | tee -a "${HEALTH_LOG}" || log "No pip config set"

# Unset any user-site config that might conflict
export PIP_USER=0
log "Set PIP_USER=0 to prevent --user flag conflicts"

# Health Check 4: Check requirements.txt
log "Health Check 4: Validating requirements.txt..."
if [ ! -f "requirements.txt" ]; then
    log_error "requirements.txt not found"
    exit 1
fi

log "Requirements.txt contents:"
cat requirements.txt | tee -a "${BUILD_LOG}"
log_success "requirements.txt found"

# Health Check 5: Check available disk space
log "Health Check 5: Checking disk space..."
df -h . | tee -a "${HEALTH_LOG}"
log_success "Disk space check complete"

# Install dependencies
log "=========================================="
log "Installing Python Dependencies"
log "=========================================="

# Clear any previous pip cache issues
log "Clearing pip cache..."
pip cache purge 2>&1 | tee -a "${BUILD_LOG}" || log "No cache to clear"

# Install with proper flags (no --user, no conflicts)
log "Running: pip install --no-warn-script-location -r requirements.txt"
if pip install --no-warn-script-location -r requirements.txt 2>&1 | tee -a "${BUILD_LOG}"; then
    log_success "Dependencies installed successfully"
else
    log_error "Failed to install dependencies"
    log "See ${BUILD_LOG} for details"
    exit 1
fi

# Post-install Health Checks
log "=========================================="
log "Post-Install Health Checks"
log "=========================================="

# Check critical packages
REQUIRED_PACKAGES=("fastapi" "uvicorn" "APScheduler" "httpx" "pydantic")

log "Verifying installed packages..."
for package in "${REQUIRED_PACKAGES[@]}"; do
    if python -c "import ${package,,}" 2>/dev/null; then
        log_success "${package} is installed and importable"
    else
        log_error "${package} is NOT importable"
        exit 1
    fi
done

# Check package versions
log "Installed package versions:"
pip list | grep -E "(fastapi|uvicorn|APScheduler|httpx|pydantic)" | tee -a "${HEALTH_LOG}"

# Create data directory
log "Creating data directory for cache..."
mkdir -p data
log_success "data/ directory ready"

# Verify project structure
log "Verifying project structure..."
REQUIRED_DIRS=("src" "src/core" "src/agents" "src/api" "src/api/routes")
for dir in "${REQUIRED_DIRS[@]}"; do
    if [ -d "${dir}" ]; then
        log_success "${dir}/ exists"
    else
        log_error "${dir}/ not found"
        exit 1
    fi
done

# Check critical files
CRITICAL_FILES=("src/core/server.py" "src/core/cache.py" "src/core/scheduler.py" "src/api/routes/cached.py")
for file in "${CRITICAL_FILES[@]}"; do
    if [ -f "${file}" ]; then
        log_success "${file} exists"
    else
        log_error "${file} not found"
        exit 1
    fi
done

# Final summary
log "=========================================="
log "Build Summary"
log "=========================================="
log_success "All health checks passed"
log_success "All dependencies installed"
log_success "Project structure validated"
log ""
log "Build logs saved to: ${BUILD_LOG}"
log "Health check logs saved to: ${HEALTH_LOG}"
log ""
log "=========================================="
log "✅ Build completed successfully!"
log "=========================================="

# Create a build success marker
echo "Build completed at $(date)" > "${LOG_DIR}/last_successful_build.txt"
echo "Build log: ${BUILD_LOG}" >> "${LOG_DIR}/last_successful_build.txt"

exit 0
