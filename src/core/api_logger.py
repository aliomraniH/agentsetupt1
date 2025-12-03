"""
API Logging and Request Tracking System

This module provides comprehensive logging for API requests, tracking:
- Request source (client application, user-agent, IP)
- API call chains (which external APIs are called)
- Sequence tracking (order of operations)
- Claude AI usage (embedded vs external)
- Response metrics and performance data
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from dataclasses import dataclass, field, asdict
from enum import Enum
import uuid
import json
from loguru import logger
from contextvars import ContextVar

# Context variable to track current request
current_request_context: ContextVar[Optional['RequestContext']] = ContextVar('current_request_context', default=None)


class RequestSource(str, Enum):
    """Types of request sources"""
    WEB_APP = "web_app"
    MOBILE_APP = "mobile_app"
    EXTERNAL_API = "external_api"
    INTERNAL_SERVICE = "internal_service"
    EMBEDDED_AI = "embedded_ai"
    THIRD_PARTY = "third_party"
    UNKNOWN = "unknown"


class APICallType(str, Enum):
    """Types of API calls"""
    STOCK_PRICE = "stock_price"
    NEWS_SEARCH = "news_search"
    CLAUDE_AI = "claude_ai"
    HEALTH_CHECK = "health_check"
    ALPHA_VANTAGE = "alpha_vantage"
    PERPLEXITY = "perplexity"
    YFINANCE = "yfinance"
    WEB_SCRAPING = "web_scraping"
    UNKNOWN = "unknown"


class ClaudeUsageType(str, Enum):
    """Types of Claude AI usage"""
    EMBEDDED = "embedded"  # Our embedded Claude agent responding
    EXTERNAL = "external"  # Third-party using their own AI
    PASSTHROUGH = "passthrough"  # Request passed to our Claude agent
    NOT_APPLICABLE = "not_applicable"


@dataclass
class ExternalAPICall:
    """Tracks calls to external APIs"""
    api_name: str
    endpoint: str
    method: str
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_ms: Optional[float] = None
    status_code: Optional[int] = None
    success: bool = False
    error: Optional[str] = None
    response_size: Optional[int] = None

    def complete(self, success: bool, status_code: Optional[int] = None,
                 error: Optional[str] = None, response_size: Optional[int] = None):
        """Mark the API call as complete"""
        self.end_time = datetime.now(timezone.utc)
        self.duration_ms = (self.end_time - self.start_time).total_seconds() * 1000
        self.success = success
        self.status_code = status_code
        self.error = error
        self.response_size = response_size


@dataclass
class RequestContext:
    """Tracks context for a single API request"""
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    start_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    # Request details
    method: str = ""
    path: str = ""
    query_params: Dict[str, Any] = field(default_factory=dict)
    headers: Dict[str, str] = field(default_factory=dict)

    # Source tracking
    source_type: RequestSource = RequestSource.UNKNOWN
    source_identifier: Optional[str] = None  # App ID, API key, or client identifier
    user_agent: Optional[str] = None
    ip_address: Optional[str] = None
    referer: Optional[str] = None

    # API call tracking
    api_call_type: APICallType = APICallType.UNKNOWN
    external_api_calls: List[ExternalAPICall] = field(default_factory=list)

    # Claude usage tracking
    claude_usage_type: ClaudeUsageType = ClaudeUsageType.NOT_APPLICABLE
    claude_model: Optional[str] = None
    claude_tokens_used: Optional[int] = None

    # Response tracking
    end_time: Optional[datetime] = None
    duration_ms: Optional[float] = None
    status_code: Optional[int] = None
    response_size: Optional[int] = None
    success: bool = False
    error: Optional[str] = None

    # Sequence tracking
    sequence_number: int = 0
    parent_request_id: Optional[str] = None
    child_request_ids: List[str] = field(default_factory=list)

    def add_external_api_call(self, api_name: str, endpoint: str, method: str = "GET") -> ExternalAPICall:
        """Add and track an external API call"""
        call = ExternalAPICall(
            api_name=api_name,
            endpoint=endpoint,
            method=method,
            start_time=datetime.now(timezone.utc)
        )
        self.external_api_calls.append(call)
        return call

    def complete(self, status_code: int, response_size: Optional[int] = None,
                 error: Optional[str] = None):
        """Mark the request as complete"""
        self.end_time = datetime.now(timezone.utc)
        self.duration_ms = (self.end_time - self.start_time).total_seconds() * 1000
        self.status_code = status_code
        self.response_size = response_size
        self.success = 200 <= status_code < 300
        self.error = error

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging"""
        data = asdict(self)
        # Convert enums to strings
        data['source_type'] = self.source_type.value
        data['api_call_type'] = self.api_call_type.value
        data['claude_usage_type'] = self.claude_usage_type.value
        # Convert datetimes to ISO format
        data['start_time'] = self.start_time.isoformat()
        if self.end_time:
            data['end_time'] = self.end_time.isoformat()
        # Convert external API calls
        data['external_api_calls'] = [
            {
                **asdict(call),
                'start_time': call.start_time.isoformat(),
                'end_time': call.end_time.isoformat() if call.end_time else None
            }
            for call in self.external_api_calls
        ]
        return data


class APILogger:
    """Central API logging service"""

    def __init__(self):
        self._sequence_counter = 0
        self._request_log: List[RequestContext] = []
        self._max_log_size = 1000  # Keep last 1000 requests in memory

    def create_request_context(
        self,
        method: str,
        path: str,
        headers: Dict[str, str],
        query_params: Dict[str, Any],
        ip_address: Optional[str] = None
    ) -> RequestContext:
        """Create a new request context"""
        self._sequence_counter += 1

        context = RequestContext(
            method=method,
            path=path,
            headers=dict(headers),
            query_params=dict(query_params),
            sequence_number=self._sequence_counter,
            ip_address=ip_address,
            user_agent=headers.get('user-agent'),
            referer=headers.get('referer')
        )

        # Determine source type from headers
        context.source_type = self._determine_source_type(headers, path)
        context.source_identifier = self._extract_source_identifier(headers)

        # Determine API call type from path
        context.api_call_type = self._determine_api_call_type(path)

        # Set the context
        current_request_context.set(context)

        # Log request start
        logger.info(
            f"📥 [{context.sequence_number}] {method} {path} | "
            f"Source: {context.source_type.value} | "
            f"Type: {context.api_call_type.value} | "
            f"ID: {context.request_id[:8]}"
        )

        return context

    def _determine_source_type(self, headers: Dict[str, str], path: str) -> RequestSource:
        """Determine the source type of the request"""
        user_agent = headers.get('user-agent', '').lower()
        x_source = headers.get('x-source-type', '').lower()
        x_client_id = headers.get('x-client-id', '').lower()

        # Check explicit source header
        if x_source:
            try:
                return RequestSource(x_source)
            except ValueError:
                pass

        # Check for embedded AI agent endpoints
        if '/embedded-ai/' in path or x_client_id == 'embedded-ai':
            return RequestSource.EMBEDDED_AI

        # Check for third-party apps
        if 'stock-report' in user_agent or x_client_id == 'stock-report':
            return RequestSource.THIRD_PARTY

        # Check for mobile apps
        if any(mobile in user_agent for mobile in ['android', 'ios', 'mobile']):
            return RequestSource.MOBILE_APP

        # Check for web browsers
        if any(browser in user_agent for browser in ['mozilla', 'chrome', 'safari', 'firefox']):
            return RequestSource.WEB_APP

        # Check for API clients
        if any(api in user_agent for api in ['curl', 'httpx', 'requests', 'postman']):
            return RequestSource.EXTERNAL_API

        return RequestSource.UNKNOWN

    def _extract_source_identifier(self, headers: Dict[str, str]) -> Optional[str]:
        """Extract a unique identifier for the request source"""
        # Try various identification headers
        return (
            headers.get('x-client-id') or
            headers.get('x-app-id') or
            headers.get('x-api-key') or
            headers.get('authorization', '').split()[-1][:16] if headers.get('authorization') else None
        )

    def _determine_api_call_type(self, path: str) -> APICallType:
        """Determine the type of API call from the path"""
        if '/stock-monitor' in path or '/stocks' in path:
            return APICallType.STOCK_PRICE
        elif '/news-search' in path or '/news' in path:
            return APICallType.NEWS_SEARCH
        elif '/claude-assistant' in path or '/ai' in path:
            return APICallType.CLAUDE_AI
        elif '/health' in path:
            return APICallType.HEALTH_CHECK
        return APICallType.UNKNOWN

    def log_external_api_call(
        self,
        api_name: str,
        endpoint: str,
        method: str = "GET"
    ) -> Optional[ExternalAPICall]:
        """Log a call to an external API"""
        context = current_request_context.get()
        if context:
            call = context.add_external_api_call(api_name, endpoint, method)
            logger.debug(
                f"  ↳ [{context.sequence_number}] Calling {api_name}: {method} {endpoint}"
            )
            return call
        return None

    def log_claude_usage(
        self,
        usage_type: ClaudeUsageType,
        model: str,
        tokens: int
    ):
        """Log Claude AI usage"""
        context = current_request_context.get()
        if context:
            context.claude_usage_type = usage_type
            context.claude_model = model
            context.claude_tokens_used = tokens
            logger.info(
                f"  🤖 [{context.sequence_number}] Claude {usage_type.value}: "
                f"{model} ({tokens} tokens)"
            )

    def complete_request(
        self,
        status_code: int,
        response_size: Optional[int] = None,
        error: Optional[str] = None
    ):
        """Mark the current request as complete"""
        context = current_request_context.get()
        if context:
            context.complete(status_code, response_size, error)

            # Log completion
            status_emoji = "✅" if context.success else "❌"
            logger.info(
                f"📤 [{context.sequence_number}] {status_emoji} {status_code} | "
                f"{context.duration_ms:.0f}ms | "
                f"External APIs: {len(context.external_api_calls)} | "
                f"ID: {context.request_id[:8]}"
            )

            # Log external API summary
            if context.external_api_calls:
                for call in context.external_api_calls:
                    call_emoji = "✓" if call.success else "✗"
                    logger.debug(
                        f"    {call_emoji} {call.api_name}: {call.duration_ms:.0f}ms | "
                        f"Status: {call.status_code or 'N/A'}"
                    )

            # Add to log history
            self._request_log.append(context)
            if len(self._request_log) > self._max_log_size:
                self._request_log = self._request_log[-self._max_log_size:]

            # Clear context
            current_request_context.set(None)

    def get_request_stats(self, last_n: int = 100) -> Dict[str, Any]:
        """Get statistics for recent requests"""
        recent_requests = self._request_log[-last_n:]

        if not recent_requests:
            return {
                "total_requests": 0,
                "message": "No requests logged yet"
            }

        # Calculate statistics
        total = len(recent_requests)
        successful = sum(1 for r in recent_requests if r.success)

        # Group by source type
        by_source = {}
        for req in recent_requests:
            source = req.source_type.value
            by_source[source] = by_source.get(source, 0) + 1

        # Group by API call type
        by_api_type = {}
        for req in recent_requests:
            api_type = req.api_call_type.value
            by_api_type[api_type] = by_api_type.get(api_type, 0) + 1

        # Track external API usage
        external_api_stats = {}
        for req in recent_requests:
            for call in req.external_api_calls:
                api = call.api_name
                if api not in external_api_stats:
                    external_api_stats[api] = {
                        "total_calls": 0,
                        "successful_calls": 0,
                        "failed_calls": 0,
                        "avg_duration_ms": 0,
                        "total_duration_ms": 0
                    }
                external_api_stats[api]["total_calls"] += 1
                if call.success:
                    external_api_stats[api]["successful_calls"] += 1
                else:
                    external_api_stats[api]["failed_calls"] += 1
                if call.duration_ms:
                    external_api_stats[api]["total_duration_ms"] += call.duration_ms

        # Calculate averages for external APIs
        for api, stats in external_api_stats.items():
            if stats["total_calls"] > 0:
                stats["avg_duration_ms"] = round(
                    stats["total_duration_ms"] / stats["total_calls"], 2
                )
                del stats["total_duration_ms"]

        # Claude usage stats
        claude_requests = [r for r in recent_requests if r.claude_usage_type != ClaudeUsageType.NOT_APPLICABLE]
        claude_stats = {
            "total_claude_requests": len(claude_requests),
            "embedded_usage": sum(1 for r in claude_requests if r.claude_usage_type == ClaudeUsageType.EMBEDDED),
            "external_usage": sum(1 for r in claude_requests if r.claude_usage_type == ClaudeUsageType.EXTERNAL),
            "passthrough_usage": sum(1 for r in claude_requests if r.claude_usage_type == ClaudeUsageType.PASSTHROUGH),
            "total_tokens_used": sum(r.claude_tokens_used or 0 for r in claude_requests)
        }

        # Average response time
        durations = [r.duration_ms for r in recent_requests if r.duration_ms]
        avg_duration = sum(durations) / len(durations) if durations else 0

        return {
            "total_requests": total,
            "successful_requests": successful,
            "failed_requests": total - successful,
            "success_rate": round((successful / total) * 100, 2),
            "avg_response_time_ms": round(avg_duration, 2),
            "requests_by_source": by_source,
            "requests_by_api_type": by_api_type,
            "external_api_usage": external_api_stats,
            "claude_usage": claude_stats,
            "time_range": {
                "start": recent_requests[0].start_time.isoformat() if recent_requests else None,
                "end": recent_requests[-1].start_time.isoformat() if recent_requests else None
            }
        }

    def get_recent_requests(self, last_n: int = 20) -> List[Dict[str, Any]]:
        """Get recent request logs"""
        recent = self._request_log[-last_n:]
        return [req.to_dict() for req in recent]

    def get_request_by_id(self, request_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific request by ID"""
        for req in reversed(self._request_log):
            if req.request_id == request_id:
                return req.to_dict()
        return None


# Global instance
api_logger = APILogger()
