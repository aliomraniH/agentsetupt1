# ⚡ Quick Deploy Reference

**1️⃣ Pull Code in Replit Shell:**
```bash
git fetch origin
git checkout claude/optimize-api-memory-017vafomh7apzPdAvRf7G1Ew
git pull
```

**2️⃣ Install Dependencies:**
```bash
pip install -r requirements.txt
```

**3️⃣ Create Data Directory:**
```bash
mkdir -p data
```

**4️⃣ Verify Secrets (Environment Variables):**
- `ALPHA_VANTAGE_API_KEY` ← **Required**
- `PERPLEXITY_API_KEY` ← Optional
- `ANTHROPIC_API_KEY` ← For Claude agent

**5️⃣ Click Run in Replit ▶**

**6️⃣ Test Deployment:**
```bash
# Check health
curl https://agentsetupt-1-aloomrani.replit.app/health

# Check cache stats
curl https://agentsetupt-1-aloomrani.replit.app/api/v1/cached/stats

# Get cached stocks
curl https://agentsetupt-1-aloomrani.replit.app/api/v1/cached/lists/top_tech
```

**✅ Success Indicators:**
- Server logs show: `✓ Background stock cache scheduler started`
- Cache stats show: `"valid_entries" > 0`
- Cached endpoints return data instantly

---

## 🔗 New Endpoints

All instant, no external API calls:

```
GET  /api/v1/cached/stocks              # All cached
GET  /api/v1/cached/stocks/{symbol}     # Single stock
GET  /api/v1/cached/stocks/batch        # Multiple
GET  /api/v1/cached/lists               # Available lists
GET  /api/v1/cached/lists/top_tech      # Tech stocks
GET  /api/v1/cached/stats               # Statistics
POST /api/v1/cached/refresh             # Manual refresh
```

---

## 🚨 Troubleshooting

**No cached data?**
```bash
# Wait 1-2 min for initial refresh, or:
curl -X POST https://agentsetupt-1-aloomrani.replit.app/api/v1/cached/refresh
```

**Module not found?**
```bash
pip install APScheduler==3.10.4
```

**Permission error?**
```bash
mkdir -p data && chmod 755 data
```

---

**📖 Full Guide:** See [DEPLOYMENT_GUIDE.md](./DEPLOYMENT_GUIDE.md)
