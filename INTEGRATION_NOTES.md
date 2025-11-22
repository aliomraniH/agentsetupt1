# Integration Notes: Claude Agent Implementation

## Two Complementary Approaches

This repository now contains **two different Claude API integrations** that serve different purposes:

### 1. Simple LLM Test Endpoint (Previous Session)
- **Location**: `/api/v1/agents/llm-test`
- **Branch**: `claude/news-search-agent-01CfUT4hSdKXcToqRvKxXxaD`
- **Purpose**: Quick API validation with 5 predefined test questions
- **Use Case**: Testing that Claude API key is working correctly

### 2. Comprehensive Claude Agent (Current Implementation)
- **Location**: `/api/v1/agents/claude-assistant/*`
- **Branch**: `claude/review-api-implementation-01MEDyg9u7BAKcDsba5di7U8`
- **Purpose**: Full-featured AI assistant with multiple capabilities
- **Use Cases**:
  - Chat conversations with history
  - Code review and generation
  - Text analysis and summarization
  - Integration with other agents (stock monitor, health monitor)

## Key Differences

| Feature | LLM Test Endpoint | Claude Agent |
|---------|------------------|--------------|
| Endpoints | 1 (`/llm-test`) | 9+ specialized endpoints |
| Capabilities | Simple Q&A testing | Chat, code review, analysis, etc. |
| History | No | Yes (last 20 messages) |
| Models | Hardcoded Sonnet | User-selectable (Opus, Sonnet, Haiku) |
| Configuration | Minimal | Full agent framework |
| Use Case | API validation | Production AI features |

## Model Name Corrections Applied

Based on previous session findings, all model names have been updated:

```python
# ✅ CORRECT (verified working)
"claude-3-5-sonnet-20241022"  # Default for all endpoints

# ❌ INCORRECT (does not exist)
"claude-3-5-sonnet-20241022"  # Was incorrectly used initially
```

**Files Updated:**
- `src/agents/claude_agent.py` - ClaudeModel enum
- `src/api/routes/agents.py` - All request model defaults
- `CLAUDE_AGENT_USAGE.md` - Documentation

## Integration with Existing Systems

### Alpha Vantage + Claude Analysis

Combine stock data from Alpha Vantage with Claude's analysis:

```bash
# 1. Get stock data (uses Alpha Vantage from previous session)
stocks=$(curl http://localhost:8080/api/v1/agents/stock-monitor/quick?debug=true)

# 2. Analyze with Claude
curl -X POST http://localhost:8080/api/v1/agents/claude-assistant/analyze \
  -H "Content-Type: application/json" \
  -d "{\"message\": \"Analyze these stock trends and provide insights: $stocks\"}"
```

### Health Monitor + Claude Reporting

Get health status and generate reports:

```bash
# 1. Run health check
health=$(curl -X POST http://localhost:8080/api/v1/agents/health-monitor/run)

# 2. Generate summary report
curl -X POST http://localhost:8080/api/v1/agents/claude-assistant/summarize \
  -H "Content-Type: application/json" \
  -d "{\"message\": \"Summarize this health report: $health\"}"
```

### News Search + Claude Summarization

(When news search agent is available)

```bash
# 1. Search for news
news=$(curl http://localhost:8080/api/v1/agents/news-search/search?query=tech)

# 2. Summarize findings
curl -X POST http://localhost:8080/api/v1/agents/claude-assistant/summarize \
  -H "Content-Type: application/json" \
  -d "{\"message\": \"Summarize these news articles: $news\"}"
```

## API Key Requirements

Both implementations use the same API key:

```bash
# In Replit Secrets or .env
ANTHROPIC_API_KEY=sk-ant-your-key-here
```

**Important:** The key must be named **exactly** `ANTHROPIC_API_KEY` (not `Anthropic_API_KEY`).

## Configuration Consistency

Both approaches use `src/core/config.py`:

```python
class Settings(BaseSettings):
    # ...
    anthropic_api_key: Optional[str] = None  # Used by both implementations
    alpha_vantage_api_key: Optional[str] = None  # For stock data
    perplexity_api_key: Optional[str] = None  # For LLM stock search
```

## Logging Enhancement

Both implementations benefit from the enhanced logging system:

```python
# From src/core/server.py
logger.add(
    sys.stdout,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level}</level> | {message}",
    level="INFO",
    colorize=True,
    backtrace=True,
    diagnose=True
)
```

**Logs visible in:** Replit → Logs tab

## Rate Limiting Considerations

### Alpha Vantage (from previous session)
- **Free Tier**: 25 API calls/day, 5 calls/minute
- **Impact**: Limits how often stock data can be refreshed
- **Fallback**: yfinance → Perplexity LLM → Web scraping

### Anthropic Claude
- **Rate Limits**: Depends on your API tier
- **Token Limits**:
  - Sonnet: 4096 tokens default (configurable)
  - Opus: Higher limits but more expensive
- **Cost**: ~$3/million input tokens, ~$15/million output tokens (Sonnet)

### Combined Usage
When chaining stock data + Claude analysis:
- Each full workflow = 1 Alpha Vantage call + 1 Claude call
- Example: 10 stocks analyzed = 10 Alpha Vantage + 1 Claude call
- **Daily capacity (free tiers)**: ~25 analyzed stock reports

## Testing Both Implementations

### Test Simple LLM Endpoint
```bash
curl https://agentsetupt-1-aloomrani.replit.app/api/v1/agents/llm-test
```

Expected: JSON with 5 test results (geography, colors, math, etc.)

### Test Comprehensive Agent
```bash
# Simple chat
curl -X POST https://agentsetupt-1-aloomrani.replit.app/api/v1/agents/claude-assistant/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello Claude!"}'

# Code review
curl -X POST https://agentsetupt-1-aloomrani.replit.app/api/v1/agents/claude-assistant/code/review \
  -H "Content-Type: application/json" \
  -d '{
    "code": "def add(a, b): return a + b",
    "language": "python"
  }'
```

## Merging Considerations

### If Merging Both Branches:

1. **Keep both implementations** - They serve different purposes
2. **Route ordering**: Ensure specific routes come before parameterized ones:
   ```python
   @router.get("/agents/llm-test")        # Specific - FIRST
   @router.get("/agents/claude-assistant/chat")  # Specific
   @router.get("/agents/{agent_name}")    # Parameterized - LAST
   ```
3. **Model names**: All must use `claude-3-5-sonnet-20241022`
4. **Shared config**: Both use same `ANTHROPIC_API_KEY`

### Conflict Resolution:

If both branches modify the same files:
- `src/core/config.py`: Should be identical (both need `anthropic_api_key`)
- `src/api/routes/agents.py`: Combine routes, fix ordering
- `requirements.txt`: Merge dependencies (both need `anthropic`)

## Future Enhancements

### Potential Improvements:
1. **Unified Agent Interface**: Create a base LLM agent class
2. **Response Caching**: Cache Claude responses to reduce API calls
3. **Streaming Support**: Add streaming endpoints for long responses
4. **Multi-Model Support**: Allow switching between providers (Claude, OpenAI, etc.)
5. **Conversation Persistence**: Save history to database
6. **Rate Limit Handling**: Implement exponential backoff for rate limits

### Integration Ideas:
1. **Automated Stock Reports**:
   - Cron job → Fetch stocks → Claude analysis → Email/Slack
2. **Health Monitoring Alerts**:
   - Service down → Claude generates incident report → Notify team
3. **News Digest**:
   - Daily news fetch → Claude summarization → Morning briefing

## Troubleshooting

### Issue: "model: claude-3-5-sonnet-20241022 not found"
**Solution**: Model name is incorrect. Update to `claude-3-5-sonnet-20241022`

### Issue: "ANTHROPIC_API_KEY not configured"
**Solution**:
1. Check Replit Secrets (exact name: `ANTHROPIC_API_KEY`)
2. Verify no typos (case-sensitive)
3. Restart deployment after adding secret

### Issue: Rate limit errors
**Solution**:
1. For Alpha Vantage: Wait for rate limit to reset (per minute/day)
2. For Claude: Upgrade API tier or implement caching
3. Use debug flags to see which tier is being used

### Issue: Route 404 errors
**Solution**: Check route ordering - specific routes must come before parameterized routes

## Documentation References

- **This Implementation**: `CLAUDE_AGENT_USAGE.md`
- **Previous Session**: Context provided in session report
- **API Docs**:
  - Anthropic: https://docs.anthropic.com/claude/reference/messages_post
  - Alpha Vantage: https://www.alphavantage.co/documentation/

## Version History

| Branch | Feature | Status |
|--------|---------|--------|
| `claude/news-search-agent-01CfUT4hSdKXcToqRvKxXxaD` | Alpha Vantage + LLM test | ✅ Working |
| `claude/review-api-implementation-01MEDyg9u7BAKcDsba5di7U8` | Comprehensive Claude Agent | ✅ Working (model fixed) |

## Contact & Support

For issues or questions:
1. Check logs in Replit → Logs tab
2. Verify API keys in Secrets
3. Test endpoints with curl commands above
4. Review error messages for specific issues

---

**Last Updated**: 2025-11-21
**Model Correction Applied**: claude-3-5-sonnet-20241022 (verified working)
