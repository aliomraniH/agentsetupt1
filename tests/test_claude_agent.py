"""
Tests for Claude Agent
"""

import pytest
from src.agents.claude_agent import ClaudeAgent, ClaudeModel, ClaudeTask


def test_agent_initialization():
    """Test that agent initializes correctly"""
    agent = ClaudeAgent()
    assert agent.name == "claude-assistant"
    assert "AI assistant" in agent.description
    assert agent.status.value == "idle"


def test_agent_history():
    """Test conversation history management"""
    agent = ClaudeAgent()

    # Initially empty
    assert len(agent.get_history()) == 0

    # Add some messages
    agent._add_to_history("user", "Hello")
    agent._add_to_history("assistant", "Hi there!")

    history = agent.get_history()
    assert len(history) == 2
    assert history[0]["role"] == "user"
    assert history[0]["content"] == "Hello"

    # Clear history
    agent.clear_history()
    assert len(agent.get_history()) == 0


def test_task_prompts():
    """Test that task prompts are defined"""
    from src.agents.claude_agent import TASK_PROMPTS

    assert ClaudeTask.CHAT in TASK_PROMPTS
    assert ClaudeTask.ANALYZE in TASK_PROMPTS
    assert ClaudeTask.SUMMARIZE in TASK_PROMPTS
    assert ClaudeTask.CODE_REVIEW in TASK_PROMPTS
    assert ClaudeTask.CODE_GENERATE in TASK_PROMPTS


def test_get_system_prompt():
    """Test system prompt selection"""
    agent = ClaudeAgent()

    # Test task-based prompts
    chat_prompt = agent._get_system_prompt(ClaudeTask.CHAT)
    assert "Claude" in chat_prompt

    analyze_prompt = agent._get_system_prompt(ClaudeTask.ANALYZE)
    assert "analyst" in analyze_prompt.lower()

    # Test custom prompt
    custom = "You are a helpful assistant"
    custom_prompt = agent._get_system_prompt(ClaudeTask.CHAT, custom)
    assert custom_prompt == custom


def test_agent_info():
    """Test agent info retrieval"""
    agent = ClaudeAgent()
    info = agent.get_info()

    assert info["name"] == "claude-assistant"
    assert "description" in info
    assert "status" in info
    assert "stats" in info


@pytest.mark.asyncio
async def test_run_without_api_key():
    """Test that running without API key raises proper error"""
    from src.core.config import settings

    agent = ClaudeAgent()

    # Save original key
    original_key = settings.anthropic_api_key
    settings.anthropic_api_key = None

    try:
        # Should raise ValueError about missing API key
        result = await agent.execute(message="Hello")
        assert result["status"] == "error"
        assert "ANTHROPIC_API_KEY" in result["error"]
    finally:
        # Restore original key
        settings.anthropic_api_key = original_key


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
