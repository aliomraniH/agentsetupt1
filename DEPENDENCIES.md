# Dependency Management

This project uses automatic dependency checking and installation to ensure compatibility.

## Automatic Dependency Checker

The `scripts/check_dependencies.py` script automatically:
- ✅ Installs all dependencies from `requirements.txt`
- ✅ Checks for version conflicts
- ✅ Verifies critical imports work
- ✅ Runs on every deployment and local startup

## Requirements

### Core Dependencies

**Web Framework:**
- `fastapi==0.115.0` - Modern async web framework
- `uvicorn[standard]==0.24.0` - ASGI server

**Data & Validation:**
- `pydantic==2.9.0` - Data validation
- `typing-extensions>=4.11,<5.0` - Type hints (required by OpenAI)

**Stock Data:**
- `yfinance==0.2.33` - Yahoo Finance API
- `beautifulsoup4==4.12.2` - Web scraping
- `lxml==5.1.0` - XML/HTML parser

**LLM Integration:**
- `openai==1.54.0` - Perplexity AI client (uses OpenAI-compatible API)

## Dependency Conflicts Fixed

### Issue: typing-extensions conflict
**Problem:** OpenAI 1.54.0 requires `typing-extensions>=4.11` but we had `==4.8.0`

**Solution:**
```diff
- typing-extensions==4.8.0
+ typing-extensions>=4.11,<5.0
```

### Issue: FastAPI/Pydantic compatibility
**Problem:** Older FastAPI/Pydantic versions incompatible with newer typing-extensions

**Solution:** Upgraded to compatible versions:
```diff
- fastapi==0.104.1
+ fastapi==0.115.0

- pydantic==2.5.2
+ pydantic==2.9.0
```

## Manual Dependency Check

Run the dependency checker manually:

```bash
python scripts/check_dependencies.py
```

Expected output:
```
🔧 Dependency Checker & Auto-Installer
========================================
📦 Installing dependencies...
✅ Dependencies installed successfully!
🔍 Checking for dependency conflicts...
✅ No dependency conflicts detected!
🧪 Verifying critical imports...
  ✅ FastAPI web framework (fastapi)
  ✅ Pydantic validation (pydantic)
  ✅ OpenAI/Perplexity client (openai)
  ✅ Yahoo Finance library (yfinance)
  ✅ Loguru logging (loguru)

✅ All dependencies installed and verified successfully!
🚀 Ready to deploy!
```

## Adding New Dependencies

1. Add to `requirements.txt` with specific version:
   ```
   new-package==1.2.3
   ```

2. Run dependency checker:
   ```bash
   python scripts/check_dependencies.py
   ```

3. If conflicts occur:
   - Check error messages
   - Adjust version constraints
   - Use `>=` instead of `==` for flexible ranges

4. Test locally before deploying

## Replit Deployment

The `.replit` configuration automatically:
- Upgrades pip during build
- Installs dependencies with `--no-user` flag (Replit requirement)
- Checks dependencies on local run

```toml
[deployment]
build = ["sh", "-c", "pip install --no-user --upgrade pip && pip install --no-user -r requirements.txt"]
run = ["python", "-m", "uvicorn", "src.core.server:app", "--host", "0.0.0.0", "--port", "8080"]
```

## Troubleshooting

### Deployment fails with "ResolutionImpossible"
- Check `requirements.txt` for version conflicts
- Use `>=` constraints for flexibility
- Run local dependency checker first

### Import errors after deployment
- Verify all dependencies in `requirements.txt`
- Check Replit logs for installation errors
- Ensure secrets (API keys) are configured

### Outdated dependencies
- Review and update versions periodically
- Test in development before production
- Use dependency checker to verify compatibility
