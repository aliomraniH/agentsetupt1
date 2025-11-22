# Replit API Key Loading Fix

## Problem Summary

The Anthropic API key configured in Replit Secrets was not being loaded by the pydantic Settings class, causing 404 errors when trying to use the Claude API.

**Root Cause:** Replit Secrets are case-sensitive environment variables, but pydantic Settings was configured with `case_sensitive = False`, preventing it from matching the exact "ANTHROPIC_API_KEY" variable name.

## Solution Overview

This fix includes three components:

1. **Configuration Fix** - Update pydantic Settings to be case-sensitive with fallback loading
2. **Enhanced Error Messages** - Better debugging information when API keys are missing
3. **Verification Tools** - Script to verify API key configuration before deployment

## Files Changed

### 1. `src/core/config.py`
- Changed `case_sensitive = False` to `case_sensitive = True`
- Added custom `__init__` method with fallback `os.environ.get()` calls
- Ensures API keys are loaded even if pydantic doesn't pick them up initially

### 2. `src/agents/claude_agent.py`
- Updated model name to `claude-3-5-sonnet-20241022` (correct working model)
- Enhanced `_get_client()` with fallback environment variable check
- Improved error messages with specific troubleshooting instructions

### 3. `src/api/routes/agents.py`
- Added `/agents/debug-keys` endpoint to check API key configuration
- Updated `test_llm_api` function with direct environment checks
- Updated all model references to `claude-3-5-sonnet-20241022`

## How to Apply the Fix

### Option 1: Apply Git Patch (If you can pull from git)

```bash
# Download the patch file
git apply /tmp/replit-api-key-fix.patch

# Or if that doesn't work
patch -p1 < /tmp/replit-api-key-fix.patch
```

### Option 2: Manual Application in Replit

The changes have already been committed locally. You can:

1. **Pull the latest changes** from the `claude/news-search-agent-01CfUT4hSdKXcToqRvKxXxaD` branch
2. **Or manually copy** the three changed files from git to Replit

### Option 3: Manual Edits

If you prefer to edit files manually, see the detailed changes below:

#### `src/core/config.py`

Add at the top:
```python
import os
```

Change line 41:
```python
# FROM:
case_sensitive = False

# TO:
case_sensitive = True  # Changed to True for Replit secrets compatibility
```

Add new `__init__` method after the `Config` class (around line 42):
```python
def __init__(self, **kwargs):
    """Custom init to handle Replit environment variables"""
    super().__init__(**kwargs)

    # Fallback: Manually check environment variables if pydantic didn't load them
    if not self.anthropic_api_key:
        env_key = os.environ.get("ANTHROPIC_API_KEY")
        if env_key and env_key.strip():
            self.anthropic_api_key = env_key.strip()
            print(f"✅ Loaded ANTHROPIC_API_KEY from environment (fallback): {env_key[:20]}...")

    if not self.alpha_vantage_api_key:
        env_key = os.environ.get("ALPHA_VANTAGE_API_KEY")
        if env_key and env_key.strip():
            self.alpha_vantage_api_key = env_key.strip()

    if not self.perplexity_api_key:
        env_key = os.environ.get("PERPLEXITY_API_KEY")
        if env_key and env_key.strip():
            self.perplexity_api_key = env_key.strip()
```

#### `src/agents/claude_agent.py`

Update model name (line 23):
```python
SONNET = "claude-3-5-sonnet-20241022"  # Latest Sonnet 3.5 (October 2024)
```

Replace the error handling in `_get_client()` (around line 82):
```python
if not settings.anthropic_api_key:
    import os
    # Try one more time to get directly from environment
    direct_key = os.environ.get("ANTHROPIC_API_KEY")
    if direct_key:
        self._client = AsyncAnthropic(api_key=direct_key)
        return self._client
    else:
        raise ValueError(
            "ANTHROPIC_API_KEY not configured. "
            "Please add it to Replit Secrets (not .env file). "
            "Key name must be exactly: ANTHROPIC_API_KEY (case-sensitive). "
            "Get your key from: https://console.anthropic.com/settings/keys"
        )
```

#### `src/api/routes/agents.py`

Add debug endpoint after `list_agents()` function:
```python
@router.get("/agents/debug-keys")
async def debug_api_keys():
    """Debug endpoint to check API key configuration"""
    import os

    env_anthropic = os.environ.get("ANTHROPIC_API_KEY")
    env_alpha = os.environ.get("ALPHA_VANTAGE_API_KEY")
    env_perplexity = os.environ.get("PERPLEXITY_API_KEY")

    return {
        "environment_variables": {
            "ANTHROPIC_API_KEY": "✅ Present" if env_anthropic else "❌ Not found",
            "ALPHA_VANTAGE_API_KEY": "✅ Present" if env_alpha else "❌ Not found",
            "PERPLEXITY_API_KEY": "✅ Present" if env_perplexity else "❌ Not found"
        },
        "settings_loaded": {
            "anthropic_api_key": "✅ Loaded" if settings.anthropic_api_key else "❌ Not loaded",
            "alpha_vantage_api_key": "✅ Loaded" if settings.alpha_vantage_api_key else "❌ Not loaded",
            "perplexity_api_key": "✅ Loaded" if settings.perplexity_api_key else "❌ Not loaded"
        },
        "key_previews": {
            "anthropic": f"{settings.anthropic_api_key[:15]}...{settings.anthropic_api_key[-4:]}" if settings.anthropic_api_key and len(settings.anthropic_api_key) > 20 else "N/A",
            "alpha_vantage": f"{settings.alpha_vantage_api_key[:10]}...{settings.alpha_vantage_api_key[-4:]}" if settings.alpha_vantage_api_key and len(settings.alpha_vantage_api_key) > 15 else "N/A",
            "perplexity": f"{settings.perplexity_api_key[:15]}...{settings.perplexity_api_key[-4:]}" if settings.perplexity_api_key and len(settings.perplexity_api_key) > 20 else "N/A"
        },
        "config": {
            "case_sensitive": "True (required for Replit Secrets)",
            "env_file": ".env"
        }
    }
```

Update `test_llm_api()` function to add environment checks at the beginning:
```python
@router.get("/agents/llm-test")
async def test_llm_api():
    """..."""
    import os

    logger.info("="*80)
    logger.info("🧪 CLAUDE API TEST - Starting verification")
    logger.info("="*80)

    # Direct environment check (bypass pydantic)
    direct_env_key = os.environ.get("ANTHROPIC_API_KEY")
    logger.info(f"🔍 Direct environment check: {'✅ Found' if direct_env_key else '❌ Not found'}")
    if direct_env_key:
        logger.info(f"   Key preview: {direct_env_key[:20]}...")

    # Check settings (pydantic-loaded)
    logger.info(f"🔍 Settings check: {'✅ Loaded' if settings.anthropic_api_key else '❌ Not loaded'}")

    # ... rest of function
```

Change all model references from `claude-3-5-sonnet-20240620` to `claude-3-5-sonnet-20241022`.

## Verification

### Before Deployment

Run the verification script to check your configuration:

```bash
python scripts/verify_api_keys.py
```

This will:
- ✅ Check if API keys exist in environment variables
- ✅ Verify pydantic Settings configuration
- ✅ Test Anthropic client initialization
- ✅ Perform a test API call
- ✅ Provide specific recommendations if issues are found

### After Deployment

Test the endpoints to verify everything works:

```bash
# 1. Check API key configuration
curl https://agentsetupt-1-aloomrani.replit.app/api/v1/agents/debug-keys

# 2. Test LLM with known-answer questions
curl https://agentsetupt-1-aloomrani.replit.app/api/v1/agents/llm-test

# 3. Test Claude chat functionality
curl -X POST https://agentsetupt-1-aloomrani.replit.app/api/v1/agents/claude-assistant/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello Claude! What is 2+2?"}'
```

## Expected Results

### Debug Keys Endpoint
```json
{
  "environment_variables": {
    "ANTHROPIC_API_KEY": "✅ Present",
    "ALPHA_VANTAGE_API_KEY": "✅ Present",
    "PERPLEXITY_API_KEY": "✅ Present"
  },
  "settings_loaded": {
    "anthropic_api_key": "✅ Loaded",
    "alpha_vantage_api_key": "✅ Loaded",
    "perplexity_api_key": "✅ Loaded"
  },
  "key_previews": {
    "anthropic": "sk-ant-api03-Ab...xyz",
    "alpha_vantage": "ABCD1234...xyz",
    "perplexity": "pplx-abc123...xyz"
  }
}
```

### LLM Test Endpoint
```json
{
  "status": "success",
  "summary": {
    "total_tests": 5,
    "passed": 5,
    "failed": 0,
    "success_rate": 100.0
  },
  "message": "All 5 tests passed! Claude API working."
}
```

## Troubleshooting

### Issue: API keys still not loading

**Check:**
1. Ensure secrets are in Replit Secrets (Tools > Secrets), not .env file
2. Secret names must be EXACT: `ANTHROPIC_API_KEY` (case-sensitive)
3. Restart deployment after adding secrets
4. Run `python scripts/verify_api_keys.py` to diagnose

### Issue: Model 404 errors

**Solution:**
- Ensure all model references use `claude-3-5-sonnet-20241022`
- The old model `claude-3-5-sonnet-20240620` returns 404

### Issue: Debug endpoint shows "Present" but "Not loaded"

**Solution:**
- This means the custom `__init__` fallback should catch it
- Check that src/core/config.py has the `__init__` method
- Restart the application

## Prevention

To prevent similar issues in the future:

1. **Always use verification script** before deployment:
   ```bash
   python scripts/verify_api_keys.py
   ```

2. **Use debug endpoint** to verify configuration after deployment:
   ```bash
   curl https://your-app.replit.app/api/v1/agents/debug-keys
   ```

3. **Check Replit Secrets** are set correctly:
   - Go to Tools > Secrets
   - Verify exact names (case-sensitive)
   - No extra spaces in values

4. **Monitor logs** for the fallback loading messages:
   ```
   ✅ Loaded ANTHROPIC_API_KEY from environment (fallback): sk-ant-api03-...
   ```

## Additional Resources

- [Anthropic API Keys](https://console.anthropic.com/settings/keys)
- [Alpha Vantage API Keys](https://www.alphavantage.co/support/#api-key)
- [Perplexity API Keys](https://docs.perplexity.ai/docs/getting-started)
- [Replit Secrets Documentation](https://docs.replit.com/programming-ide/workspace-features/secrets)

## Commit Information

- **Branch:** `claude/news-search-agent-01CfUT4hSdKXcToqRvKxXxaD`
- **Commits:**
  - `786a3e5` - fix: update Claude model to claude-3-5-sonnet-20241022
  - `dd60e4d` - Fix Replit Secrets API key loading with comprehensive improvements
