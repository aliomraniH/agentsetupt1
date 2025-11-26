"""
Claude Agent - AI assistant powered by Anthropic's Claude API
"""

from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
from enum import Enum
from loguru import logger

try:
    from anthropic import Anthropic, AsyncAnthropic
except ImportError:
    Anthropic = None
    AsyncAnthropic = None

from src.agents.base import BaseAgent
from src.core.config import settings


class ClaudeModel(str, Enum):
    """Available Claude models - Latest versions (Jan 2025)"""
    # Sonnet models (best balance of intelligence and speed)
    SONNET_V2 = "claude-3-5-sonnet-20241022"  # Latest Sonnet v2 (Oct 2024) - Most capable
    SONNET = "claude-3-5-sonnet-20240620"  # Sonnet v1 (June 2024) - Fallback

    # Haiku (fastest and most economical)
    HAIKU = "claude-3-5-haiku-20241022"  # Latest Haiku (Oct 2024)

    # Opus (maximum intelligence, higher cost)
    OPUS = "claude-3-opus-20240229"  # Opus (Feb 2024)


class ClaudeTask(str, Enum):
    """Pre-defined task types"""
    CHAT = "chat"
    ANALYZE = "analyze"
    SUMMARIZE = "summarize"
    CODE_REVIEW = "code_review"
    CODE_GENERATE = "code_generate"
    TRANSLATE = "translate"
    CUSTOM = "custom"


# System prompts for different tasks
TASK_PROMPTS = {
    ClaudeTask.ANALYZE: "You are an expert analyst. Analyze the following content thoroughly and provide detailed insights.",
    ClaudeTask.SUMMARIZE: "You are an expert at summarization. Provide a clear, concise summary of the following content.",
    ClaudeTask.CODE_REVIEW: "You are an expert code reviewer. Review the following code for bugs, security issues, performance problems, and best practices. Provide specific, actionable feedback.",
    ClaudeTask.CODE_GENERATE: "You are an expert software engineer. Generate clean, well-documented, and efficient code based on the requirements.",
    ClaudeTask.TRANSLATE: "You are an expert translator. Translate the following text accurately while preserving the original meaning and tone.",
    ClaudeTask.CHAT: "You are Claude, a helpful AI assistant created by Anthropic. You are thoughtful, knowledgeable, and eager to help with a wide range of tasks."
}


class ClaudeAgent(BaseAgent):
    """
    Agent for interacting with Anthropic's Claude API.

    Provides various AI capabilities:
    - General conversation
    - Text analysis and summarization
    - Code review and generation
    - Translation
    - Custom tasks with system prompts

    Can be triggered via API for use with web services or other agents.
    """

    def __init__(self):
        super().__init__()
        self._client: Optional[AsyncAnthropic] = None
        self._conversation_history: List[Dict[str, str]] = []
        self._max_history_length = 20  # Keep last 20 messages

    @property
    def name(self) -> str:
        return "claude-assistant"

    @property
    def description(self) -> str:
        return "AI assistant powered by Anthropic's Claude for various tasks including analysis, coding, and conversation"

    def _get_client(self) -> AsyncAnthropic:
        """Get or create Anthropic client"""
        if AsyncAnthropic is None:
            raise RuntimeError("anthropic package not installed. Install with: pip install anthropic")

        if not settings.anthropic_api_key:
            import os
            # Try one more time to get directly from environment
            direct_key = os.environ.get("ANTHROPIC_API_KEY")
            if direct_key:
                # Use the direct key if found
                self._client = AsyncAnthropic(api_key=direct_key)
                return self._client
            else:
                raise ValueError(
                    "ANTHROPIC_API_KEY not configured. "
                    "Please add it to Replit Secrets (not .env file). "
                    "Key name must be exactly: ANTHROPIC_API_KEY (case-sensitive). "
                    "Get your key from: https://console.anthropic.com/settings/keys"
                )

        if self._client is None:
            self._client = AsyncAnthropic(api_key=settings.anthropic_api_key)

        return self._client

    def _get_system_prompt(self, task: ClaudeTask, custom_system: Optional[str] = None) -> str:
        """Get system prompt based on task type"""
        if custom_system:
            return custom_system
        return TASK_PROMPTS.get(task, TASK_PROMPTS[ClaudeTask.CHAT])

    def _add_to_history(self, role: str, content: str):
        """Add message to conversation history"""
        self._conversation_history.append({
            "role": role,
            "content": content
        })

        # Keep only recent messages
        if len(self._conversation_history) > self._max_history_length:
            self._conversation_history = self._conversation_history[-self._max_history_length:]

    def clear_history(self):
        """Clear conversation history"""
        self._conversation_history = []
        logger.info(f"[{self.name}] Conversation history cleared")

    def get_history(self) -> List[Dict[str, str]]:
        """Get conversation history"""
        return self._conversation_history.copy()

    async def _make_api_call(
        self,
        message: str,
        model: str,
        system: str,
        max_tokens: int,
        temperature: float,
        use_history: bool
    ) -> Dict[str, Any]:
        """Make API call to Claude with automatic fallback for newer models"""
        client = self._get_client()

        # Prepare messages
        messages = []
        if use_history and self._conversation_history:
            messages = self._conversation_history.copy()

        messages.append({
            "role": "user",
            "content": message
        })

        # Try the requested model first, with fallback for newer models
        models_to_try = [model]

        # If trying the latest Sonnet v2, add fallback to v1
        if model == ClaudeModel.SONNET_V2.value:
            models_to_try.append(ClaudeModel.SONNET.value)
            logger.info(f"[{self.name}] Attempting latest model {model} with fallback")

        last_error = None
        for attempt_model in models_to_try:
            try:
                # Make API call
                response = await client.messages.create(
                    model=attempt_model,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    system=system,
                    messages=messages
                )

                # Extract response
                assistant_message = response.content[0].text

                # Update history if enabled
                if use_history:
                    self._add_to_history("user", message)
                    self._add_to_history("assistant", assistant_message)

                # Log if we used a fallback model
                if attempt_model != model:
                    logger.warning(f"[{self.name}] Used fallback model {attempt_model} instead of {model}")

                return {
                    "response": assistant_message,
                    "model": attempt_model,  # Return actual model used
                    "requested_model": model,  # Also return requested model
                    "usage": {
                        "input_tokens": response.usage.input_tokens,
                        "output_tokens": response.usage.output_tokens,
                        "total_tokens": response.usage.input_tokens + response.usage.output_tokens
                    },
                    "stop_reason": response.stop_reason,
                    "history_length": len(self._conversation_history)
                }

            except Exception as e:
                error_str = str(e)
                # Check if it's a 404/not_found error
                if "404" in error_str or "not_found" in error_str.lower():
                    logger.warning(f"[{self.name}] Model {attempt_model} not available (404), trying fallback...")
                    last_error = e
                    continue
                else:
                    # For other errors, raise immediately
                    raise

        # If we get here, all models failed
        raise last_error if last_error else Exception("All model attempts failed")

    async def run(
        self,
        message: str,
        task: str = "chat",
        model: str = ClaudeModel.SONNET_V2.value,  # Use latest model by default
        system_prompt: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 1.0,
        use_conversation_history: bool = False,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Execute Claude AI task.

        Args:
            message: The user message/prompt
            task: Task type (chat, analyze, summarize, code_review, code_generate, translate, custom)
            model: Claude model to use (opus, sonnet, haiku)
            system_prompt: Custom system prompt (overrides task-based prompt)
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature (0-1)
            use_conversation_history: Whether to include conversation history

        Returns:
            Dict containing Claude's response and metadata
        """
        if not message:
            raise ValueError("Message is required")

        # Validate and convert task
        try:
            task_enum = ClaudeTask(task.lower())
        except ValueError:
            logger.warning(f"Unknown task '{task}', using 'chat'")
            task_enum = ClaudeTask.CHAT

        # Get system prompt
        system = self._get_system_prompt(task_enum, system_prompt)

        logger.info(f"[{self.name}] Processing {task_enum.value} request with {model}")

        try:
            result = await self._make_api_call(
                message=message,
                model=model,
                system=system,
                max_tokens=max_tokens,
                temperature=temperature,
                use_history=use_conversation_history
            )

            return {
                "task": task_enum.value,
                "message": message,
                **result
            }

        except Exception as e:
            logger.error(f"[{self.name}] API call failed: {e}")
            raise

    async def chat(self, message: str, **kwargs) -> str:
        """Convenience method for chat"""
        result = await self.run(message=message, task="chat", use_conversation_history=True, **kwargs)
        return result["response"]

    async def analyze(self, text: str, **kwargs) -> str:
        """Convenience method for analysis"""
        result = await self.run(message=text, task="analyze", **kwargs)
        return result["response"]

    async def summarize(self, text: str, **kwargs) -> str:
        """Convenience method for summarization"""
        result = await self.run(message=text, task="summarize", **kwargs)
        return result["response"]

    async def review_code(self, code: str, language: str = "python", **kwargs) -> str:
        """Convenience method for code review"""
        message = f"Review this {language} code:\n\n```{language}\n{code}\n```"
        result = await self.run(message=message, task="code_review", **kwargs)
        return result["response"]

    async def generate_code(self, requirements: str, language: str = "python", **kwargs) -> str:
        """Convenience method for code generation"""
        message = f"Generate {language} code for the following requirements:\n\n{requirements}"
        result = await self.run(message=message, task="code_generate", **kwargs)
        return result["response"]


# Singleton instance
claude_agent = ClaudeAgent()
