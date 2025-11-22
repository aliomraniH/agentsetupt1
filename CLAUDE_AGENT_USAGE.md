# Claude Agent - Usage Guide

The Claude Agent integrates Anthropic's Claude API into the backend system, providing AI-powered capabilities for various tasks.

## Setup

### 1. Install Dependencies

```bash
pip install anthropic
```

### 2. Configure API Key

Set your Anthropic API key as an environment variable:

```bash
export ANTHROPIC_API_KEY="your-api-key-here"
```

Or add it to your `.env` file:

```
ANTHROPIC_API_KEY=your-api-key-here
```

## Available Endpoints

### General Task Execution

**POST** `/api/v1/agents/claude-assistant/run`

Execute any Claude AI task with full control over parameters.

```bash
curl -X POST http://localhost:8080/api/v1/agents/claude-assistant/run \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Explain quantum computing in simple terms",
    "task": "chat",
    "model": "claude-3-5-sonnet-20241022",
    "max_tokens": 1024,
    "temperature": 1.0
  }'
```

**Available Tasks:**
- `chat` - General conversation (supports history)
- `analyze` - Analyze and provide insights
- `summarize` - Summarize content
- `code_review` - Review code for issues
- `code_generate` - Generate code from requirements
- `translate` - Translate text
- `custom` - Use custom system prompt

### Simple Chat

**POST** `/api/v1/agents/claude-assistant/chat`

Simple conversational interface with automatic history tracking.

```bash
curl -X POST http://localhost:8080/api/v1/agents/claude-assistant/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Hello! How are you today?"
  }'
```

### Text Analysis

**POST** `/api/v1/agents/claude-assistant/analyze`

Analyze text and get detailed insights.

```bash
curl -X POST http://localhost:8080/api/v1/agents/claude-assistant/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "message": "The company reported Q4 earnings of $2.5B, up 15% YoY..."
  }'
```

### Text Summarization

**POST** `/api/v1/agents/claude-assistant/summarize`

Get concise summaries of longer content.

```bash
curl -X POST http://localhost:8080/api/v1/agents/claude-assistant/summarize \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Long article text here..."
  }'
```

### Code Review

**POST** `/api/v1/agents/claude-assistant/code/review`

Review code for bugs, security issues, and best practices.

```bash
curl -X POST http://localhost:8080/api/v1/agents/claude-assistant/code/review \
  -H "Content-Type: application/json" \
  -d '{
    "code": "def calculate_total(items):\n    total = 0\n    for item in items:\n        total += item\n    return total",
    "language": "python"
  }'
```

### Code Generation

**POST** `/api/v1/agents/claude-assistant/code/generate`

Generate code based on requirements.

```bash
curl -X POST http://localhost:8080/api/v1/agents/claude-assistant/code/generate \
  -H "Content-Type: application/json" \
  -d '{
    "requirements": "Create a function that validates email addresses using regex",
    "language": "python"
  }'
```

### Agent Status

**GET** `/api/v1/agents/claude-assistant/status`

Get current status and last result.

```bash
curl http://localhost:8080/api/v1/agents/claude-assistant/status
```

### Conversation History

**GET** `/api/v1/agents/claude-assistant/history`

Retrieve conversation history.

```bash
curl http://localhost:8080/api/v1/agents/claude-assistant/history
```

**POST** `/api/v1/agents/claude-assistant/history/clear`

Clear conversation history.

```bash
curl -X POST http://localhost:8080/api/v1/agents/claude-assistant/history/clear
```

### Available Models

**GET** `/api/v1/agents/claude-assistant/models`

List available Claude models.

```bash
curl http://localhost:8080/api/v1/agents/claude-assistant/models
```

## Available Models

- **claude-3-5-sonnet-20240620** (Recommended) ✅ VERIFIED WORKING
  - Balanced performance and speed
  - Best for most use cases
  - **Note:** This is the correct model name (verified in production)

- **claude-3-opus-20240229**
  - Most capable model
  - Best for complex tasks requiring deep reasoning

- **claude-3-5-haiku-20241022**
  - Fastest and most economical
  - Best for simple tasks and high-volume requests

## Python Usage Example

```python
from src.agents.claude_agent import claude_agent

# Simple chat
async def chat_example():
    result = await claude_agent.execute(
        message="What is the capital of France?",
        task="chat"
    )
    print(result["result"]["response"])

# Code review
async def review_example():
    code = """
    def add_numbers(a, b):
        return a + b
    """
    result = await claude_agent.execute(
        message=f"Review this Python code:\n\n```python\n{code}\n```",
        task="code_review"
    )
    print(result["result"]["review"])

# With conversation history
async def conversation_example():
    # First message
    result1 = await claude_agent.execute(
        message="I'm working on a Python web app",
        task="chat",
        use_conversation_history=True
    )

    # Follow-up (remembers context)
    result2 = await claude_agent.execute(
        message="What framework do you recommend?",
        task="chat",
        use_conversation_history=True
    )
```

## Features

- **Multiple Task Types**: Chat, analysis, summarization, code review, code generation, translation
- **Conversation History**: Maintains context across multiple interactions
- **Multiple Models**: Choose from Opus, Sonnet, or Haiku based on your needs
- **Custom System Prompts**: Override default behavior with custom instructions
- **Token Usage Tracking**: Monitor API usage for each request
- **Error Handling**: Graceful error handling with detailed error messages
- **Async Support**: Fully async implementation for high performance

## Response Format

All endpoints return a standardized response:

```json
{
  "run_id": "abc12345",
  "agent": "claude-assistant",
  "status": "success",
  "started_at": "2024-01-15T10:30:00Z",
  "completed_at": "2024-01-15T10:30:05Z",
  "execution_time_seconds": 5.2,
  "result": {
    "task": "chat",
    "message": "Hello!",
    "response": "Hi! How can I help you today?",
    "model": "claude-3-5-sonnet-20241022",
    "usage": {
      "input_tokens": 12,
      "output_tokens": 25,
      "total_tokens": 37
    },
    "stop_reason": "end_turn",
    "history_length": 2
  }
}
```

## Best Practices

1. **Use the right model**: Sonnet for most tasks, Opus for complex reasoning, Haiku for simple/high-volume
2. **Enable history for conversations**: Use `use_conversation_history: true` for multi-turn chats
3. **Monitor token usage**: Check the `usage` field to track costs
4. **Set appropriate max_tokens**: Adjust based on expected response length
5. **Clear history when needed**: Clear conversation history when switching contexts
6. **Use specific task types**: Use specialized endpoints (analyze, summarize, etc.) for better results

## Troubleshooting

### API Key Not Configured

If you get an error about `ANTHROPIC_API_KEY`:

```
ValueError: ANTHROPIC_API_KEY not configured. Set it in environment variables or .env file
```

Make sure to set your API key:

```bash
export ANTHROPIC_API_KEY="your-key-here"
```

### Rate Limiting

If you hit rate limits, consider:
- Using Haiku model for high-volume requests
- Implementing request queuing
- Caching responses for repeated queries

### Memory Issues with History

If conversation history gets too long:
- Clear history periodically using `/history/clear`
- The agent automatically keeps only the last 20 messages
- Disable history for one-off queries

## Integration Examples

### With Health Monitor

Check system health and ask Claude to analyze:

```bash
# Get health status
health=$(curl http://localhost:8080/api/v1/agents/health-monitor/run)

# Ask Claude to analyze
curl -X POST http://localhost:8080/api/v1/agents/claude-assistant/analyze \
  -d "{\"message\": \"Analyze this health report: $health\"}"
```

### With Stock Monitor

Get stock data and ask for investment advice:

```bash
# Get stock data
stocks=$(curl http://localhost:8080/api/v1/agents/stock-monitor/quick)

# Ask Claude for analysis
curl -X POST http://localhost:8080/api/v1/agents/claude-assistant/analyze \
  -d "{\"message\": \"Based on this stock data, what are the trends? $stocks\"}"
```

## API Documentation

Full API documentation is available at:
- Swagger UI: `http://localhost:8080/docs`
- ReDoc: `http://localhost:8080/redoc`
