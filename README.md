# Back End Health Agent

Replit backend for hosting AI agents and engines with health monitoring capabilities.

## Overview

This project provides a modular backend system that:
- Hosts multiple AI agents as independent services
- Uses GitHub Actions for CI/CD per agent
- Exposes REST APIs for triggers and management
- Supports continuous running and on-demand execution

## Quick Start

### Running Locally

```bash
# Install dependencies
pip install -r requirements.txt

# Run the server
python -m uvicorn src.core.server:app --host 0.0.0.0 --port 8080 --reload
```

### Running on Replit

1. Import this repository into Replit
2. Click "Run" - it will automatically start the FastAPI server
3. Access the API at your Replit URL

## API Endpoints

### Health Checks

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Quick health check |
| `/health/detailed` | GET | Detailed health with system info |
| `/ready` | GET | Readiness probe |
| `/live` | GET | Liveness probe |

### Agents

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/agents` | GET | List all agents |
| `/api/v1/agents/{name}` | GET | Get agent info |
| `/api/v1/agents/health-monitor/run` | POST | Run health check |
| `/api/v1/agents/health-monitor/status` | GET | Get last check result |
| `/api/v1/agents/health-monitor/history` | GET | Get check history |
| `/api/v1/agents/health-monitor/targets` | GET | List monitoring targets |
| `/api/v1/agents/health-monitor/targets` | POST | Add monitoring target |
| `/api/v1/agents/health-monitor/targets/{id}` | DELETE | Remove target |
| `/api/v1/agents/claude-assistant/run` | POST | Execute Claude AI task |
| `/api/v1/agents/claude-assistant/chat` | POST | Simple chat with Claude |
| `/api/v1/agents/claude-assistant/analyze` | POST | Analyze text |
| `/api/v1/agents/claude-assistant/code/review` | POST | Review code |
| `/api/v1/agents/claude-assistant/code/generate` | POST | Generate code |

### Cached Data (Optimized for Third-Party Access)

**NEW: Ultra-fast cached stock endpoints** - No external API calls, instant responses!

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/cached/stocks` | GET | Get all cached stocks |
| `/api/v1/cached/stocks/{symbol}` | GET | Get single stock from cache |
| `/api/v1/cached/stocks/batch` | GET | Get multiple stocks (query params) |
| `/api/v1/cached/lists` | GET | Get available stock lists |
| `/api/v1/cached/lists/{list_name}` | GET | Get all stocks from a specific list |
| `/api/v1/cached/stats` | GET | Get cache statistics |
| `/api/v1/cached/refresh` | POST | Trigger manual cache refresh |

**Example: Get all cached tech stocks:**
```bash
curl http://localhost:8080/api/v1/cached/lists/top_tech
```

**Perfect for:**
- Claude Artifacts (no CSP restrictions on your domain!)
- Third-party dashboards
- Real-time stock displays
- Mobile apps

**Key Features:**
- ⚡ **Instant responses** - No external API calls
- 💾 **Persistent cache** - Survives server restarts (SQLite)
- 🔄 **Auto-refresh** - Background updates every 30 minutes
- 📉 **Reduced API costs** - 48 calls/day vs 288+
- 🌐 **CORS enabled** - Works from any domain

### API Documentation

- Swagger UI: `/docs`
- ReDoc: `/redoc`
- OpenAPI JSON: `/openapi.json`

## Available Agents

### Health Monitor Agent

Monitors health of deployment environments.

**Run a health check:**
```bash
curl -X POST http://localhost:8080/api/v1/agents/health-monitor/run
```

**Add a monitoring target:**
```bash
curl -X POST http://localhost:8080/api/v1/agents/health-monitor/targets \
  -H "Content-Type: application/json" \
  -d '{
    "target_id": "my-service",
    "name": "My Service",
    "url": "https://my-service.com/health",
    "service_type": "external",
    "timeout": 30
  }'
```

### Stock Monitor Agent

Fetches real-time stock market data.

**Quick stock check:**
```bash
curl http://localhost:8080/api/v1/agents/stock-monitor/quick
```

### Claude AI Agent

AI assistant powered by Anthropic's Claude API.

**Set up API key:**
```bash
export ANTHROPIC_API_KEY="your-api-key-here"
```

**Simple chat:**
```bash
curl -X POST http://localhost:8080/api/v1/agents/claude-assistant/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Explain quantum computing in simple terms"
  }'
```

**Code review:**
```bash
curl -X POST http://localhost:8080/api/v1/agents/claude-assistant/code/review \
  -H "Content-Type: application/json" \
  -d '{
    "code": "def hello(): print(\"Hello\")",
    "language": "python"
  }'
```

**Full documentation:** See [CLAUDE_AGENT_USAGE.md](./CLAUDE_AGENT_USAGE.md) for detailed usage guide

**Integration Examples:**

```bash
# Get stock data analysis with Claude
stocks=$(curl http://localhost:8080/api/v1/agents/stock-monitor/quick)
curl -X POST http://localhost:8080/api/v1/agents/claude-assistant/analyze \
  -H "Content-Type: application/json" \
  -d "{\"message\": \"Analyze this stock data: $stocks\"}"
```

## GitHub Actions

### Workflows

- **main-deploy.yml**: Main deployment workflow (tests, lint, deploy)
- **health-monitor-agent.yml**: Scheduled health checks (hourly)
- **agent-template.yml**: Template for new agent workflows

### Required Secrets

Add these to your GitHub repository settings:

| Secret | Description |
|--------|-------------|
| `BACKEND_URL` | Your Replit deployment URL |
| `REPLIT_DEPLOY_TOKEN` | Replit deployment token (optional) |
| `API_KEY` | API authentication key (optional) |

## Project Structure

```
agentsetupt1/
├── .github/workflows/      # GitHub Actions workflows
├── src/
│   ├── core/               # Core server and config
│   │   ├── server.py       # FastAPI application
│   │   └── config.py       # Settings management
│   ├── api/routes/         # API endpoints
│   │   ├── health.py       # Health check routes
│   │   └── agents.py       # Agent management routes
│   └── agents/             # Agent implementations
│       ├── base.py         # Base agent class
│       ├── health_monitor.py # Health Monitor Agent
│       ├── stock_monitor.py  # Stock Monitor Agent
│       └── claude_agent.py   # Claude AI Agent
├── tests/                  # Test files
├── .replit                 # Replit configuration
├── replit.nix              # Nix dependencies
└── requirements.txt        # Python dependencies
```

## Adding New Agents

1. Create a new file in `src/agents/`
2. Inherit from `BaseAgent`
3. Implement `name`, `description`, and `run()` method
4. Add routes in `src/api/routes/agents.py`
5. Create a GitHub workflow using `agent-template.yml`

Example:
```python
from src.agents.base import BaseAgent

class MyAgent(BaseAgent):
    @property
    def name(self) -> str:
        return "my-agent"

    @property
    def description(self) -> str:
        return "Description of what this agent does"

    async def run(self, **kwargs):
        # Agent logic here
        return {"result": "success"}
```

## Configuration

Environment variables (set in `.env` or Replit Secrets):

| Variable | Default | Description |
|----------|---------|-------------|
| `DEBUG` | `false` | Enable debug mode |
| `PORT` | `8080` | Server port |
| `API_KEY` | - | API authentication key |
| `ANTHROPIC_API_KEY` | - | For Claude integration |

## Development

### Running Tests

```bash
pytest tests/ -v
```

### Code Style

```bash
pip install ruff
ruff check src/
```

## License

MIT
