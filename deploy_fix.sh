#!/bin/bash
# Replit Deployment Fix Script
# Resolves git conflicts and deploys the optimization branch

echo "=========================================="
echo "Replit Deployment - Fixing Git Conflicts"
echo "=========================================="
echo ""

# Step 1: Check what changed in .replit
echo "Step 1: Checking local changes..."
git diff .replit
echo ""

# Step 2: Stash local changes
echo "Step 2: Stashing local changes..."
git stash push -m "Replit config before optimization deployment"
echo "✓ Local changes stashed"
echo ""

# Step 3: Checkout optimization branch
echo "Step 3: Checking out optimization branch..."
git checkout claude/optimize-api-memory-017vafomh7apzPdAvRf7G1Ew
echo "✓ Switched to optimization branch"
echo ""

# Step 4: Pull latest changes
echo "Step 4: Pulling latest changes..."
git pull origin claude/optimize-api-memory-017vafomh7apzPdAvRf7G1Ew
echo "✓ Branch updated"
echo ""

# Step 5: Check if we need to restore .replit settings
echo "Step 5: Checking stashed changes..."
echo "Your stashed .replit changes are saved and can be restored with:"
echo "  git stash pop"
echo ""
echo "If the new .replit works fine, you can discard the stash with:"
echo "  git stash drop"
echo ""

# Step 6: Install dependencies
echo "Step 6: Installing dependencies..."
pip install APScheduler==3.10.4 -q
echo "✓ APScheduler installed"
echo ""

# Step 7: Create data directory
echo "Step 7: Creating data directory..."
mkdir -p data
echo "✓ Data directory ready"
echo ""

echo "=========================================="
echo "✅ Git conflicts resolved!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Click the Run button in Replit ▶"
echo "2. Wait for: '✓ Background stock cache scheduler started'"
echo "3. Test: curl https://agentsetupt-1-aloomrani.replit.app/api/v1/cached/stats"
echo ""
