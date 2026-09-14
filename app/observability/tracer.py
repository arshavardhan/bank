"""Observability and cost analytics layer integrating Langfuse with a built-in real-time cost tracker."""

import time
import uuid
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from contextlib import contextmanager

from app.config.settings import settings

logger = logging.getLogger("financial_agent.tracer")

try:
    from langfuse import Langfuse
except ImportError:
    Langfuse = None

# Pricing table per 1,000,000 tokens (USD)
# Reference: Current pricing rates
MODEL_PRICING = {
    "local-deterministic": {"input": 0.0, "output": 0.0},
    "gemini-2.5-flash": {"input": 0.075, "output": 0.30},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "gpt-4o": {"input": 2.50, "output": 10.00}
}

# Naive approach baseline: 25,000 tokens sent directly to GPT-4o per query
NAIVE_BASELINE_TOKENS = 25000
NAIVE_BASELINE_COST_PER_REQ = (NAIVE_BASELINE_TOKENS / 1_000_000) * MODEL_PRICING["gpt-4o"]["input"]


class CostTrackerStore:
    """Tracks per-request token usage, latency, dollar cost, and architectural savings."""

    def __init__(self, max_history: int = 100):
        self.max_history = max_history
        self.traces: List[Dict[str, Any]] = []

    def record_request(
        self,
        question: str,
        tools_used: List[str],
        latency_ms: float,
        model_name: str,
        input_tokens: Optional[int] = None,
        output_tokens: Optional[int] = None,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        # Estimate tokens if not directly supplied (1 token ~= 4 chars)
        if input_tokens is None:
            input_tokens = max(len(question) // 4 + 120, 150)
        if output_tokens is None:
            output_tokens = 95

        total_tokens = input_tokens + output_tokens

        # Determine pricing model
        effective_model = model_name.lower()
        if "gemini" in effective_model:
            rates = MODEL_PRICING["gemini-2.5-flash"]
        elif "gpt-4o-mini" in effective_model:
            rates = MODEL_PRICING["gpt-4o-mini"]
        elif "local" in effective_model or not (settings.GEMINI_API_KEY or settings.OPENAI_API_KEY):
            rates = MODEL_PRICING["local-deterministic"]
            effective_model = "local-deterministic (Offline CPU)"
        else:
            rates = MODEL_PRICING["gemini-2.5-flash"]

        cost_usd = (input_tokens / 1_000_000 * rates["input"]) + (output_tokens / 1_000_000 * rates["output"])
        cost_inr = cost_usd * 85.0  # Approx USD to INR rate

        # Savings compared to naive approach of dumping entire statement to GPT-4o
        saved_usd = max(NAIVE_BASELINE_COST_PER_REQ - cost_usd, 0.0)
        saved_inr = saved_usd * 85.0

        trace_entry = {
            "id": f"req_{uuid.uuid4().hex[:8]}",
            "timestamp": datetime.now(timezone.utc).strftime("%H:%M:%S UTC"),
            "question": question,
            "session_id": session_id or "default",
            "tools_used": tools_used,
            "latency_ms": round(latency_ms, 1),
            "model": effective_model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": total_tokens,
            "cost_usd": round(cost_usd, 6),
            "cost_inr": round(cost_inr, 4),
            "saved_usd": round(saved_usd, 4),
            "saved_inr": round(saved_inr, 2)
        }

        self.traces.insert(0, trace_entry)
        if len(self.traces) > self.max_history:
            self.traces.pop()

        return trace_entry

    def get_summary(self) -> Dict[str, Any]:
        total_reqs = len(self.traces)
        if total_reqs == 0:
            return {
                "total_requests": 0,
                "total_tokens": 0,
                "total_cost_usd": 0.0,
                "total_cost_inr": 0.0,
                "total_saved_usd": 0.0,
                "total_saved_inr": 0.0,
                "avg_latency_ms": 0.0,
                "traces": [],
                "langfuse": {
                    "connected": bool(settings.LANGFUSE_PUBLIC_KEY and settings.LANGFUSE_SECRET_KEY and Langfuse is not None),
                    "host": settings.LANGFUSE_HOST,
                    "keys_configured": bool(settings.LANGFUSE_PUBLIC_KEY)
                }
            }

        total_tokens = sum(t["total_tokens"] for t in self.traces)
        total_cost_usd = round(sum(t["cost_usd"] for t in self.traces), 6)
        total_cost_inr = round(total_cost_usd * 85.0, 3)
        total_saved_usd = round(sum(t["saved_usd"] for t in self.traces), 4)
        total_saved_inr = round(total_saved_usd * 85.0, 2)
        avg_latency = round(sum(t["latency_ms"] for t in self.traces) / total_reqs, 1)

        return {
            "total_requests": total_reqs,
            "total_tokens": total_tokens,
            "total_cost_usd": total_cost_usd,
            "total_cost_inr": total_cost_inr,
            "total_saved_usd": total_saved_usd,
            "total_saved_inr": total_saved_inr,
            "avg_latency_ms": avg_latency,
            "traces": self.traces,
            "langfuse": {
                "connected": bool(settings.LANGFUSE_PUBLIC_KEY and settings.LANGFUSE_SECRET_KEY and Langfuse is not None),
                "host": settings.LANGFUSE_HOST,
                "keys_configured": bool(settings.LANGFUSE_PUBLIC_KEY)
            }
        }


cost_store = CostTrackerStore()


class ObservabilityTracer:
    """Manages Langfuse tracing lifecycle with zero-overhead graceful fallback and built-in cost tracking."""

    def __init__(self):
        self.enabled = bool(
            settings.LANGFUSE_PUBLIC_KEY and
            settings.LANGFUSE_SECRET_KEY and
            Langfuse is not None
        )
        self.client: Optional[Any] = None
        if self.enabled:
            try:
                self.client = Langfuse(
                    public_key=settings.LANGFUSE_PUBLIC_KEY,
                    secret_key=settings.LANGFUSE_SECRET_KEY,
                    host=settings.LANGFUSE_HOST
                )
                logger.info("Langfuse observability successfully initialized.")
            except Exception as e:
                logger.warning(f"Failed to initialize Langfuse: {e}")
                self.enabled = False

    def create_trace(self, name: str, user_id: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None):
        """Creates a top-level Langfuse trace or a mock trace."""
        if self.enabled and self.client:
            try:
                return self.client.trace(
                    name=name,
                    user_id=user_id,
                    metadata=metadata or {}
                )
            except Exception as e:
                logger.warning(f"Error creating Langfuse trace: {e}")
        return MockTrace(name=name)

    @contextmanager
    def trace_span(self, trace: Any, name: str, input_data: Optional[Any] = None):
        """Context manager to measure latency, inputs, and outputs of orchestrator components."""
        start_time = time.time()
        span = None
        if self.enabled and trace and hasattr(trace, "span"):
            try:
                span = trace.span(name=name, input=input_data)
            except Exception:
                span = None

        ctx = {"output": None, "error": None}
        try:
            yield ctx
        except Exception as exc:
            ctx["error"] = str(exc)
            duration = time.time() - start_time
            if span:
                try:
                    span.end(output=ctx.get("output"), level="ERROR", status_message=str(exc))
                except Exception:
                    pass
            logger.error(f"[Trace: {name}] Failed after {duration:.3f}s: {exc}")
            raise
        else:
            duration = time.time() - start_time
            if span:
                try:
                    span.end(output=ctx.get("output"), level="DEFAULT")
                except Exception:
                    pass
            logger.debug(f"[Trace: {name}] Completed in {duration:.3f}s")


class MockTrace:
    """Mock trace object when Langfuse is not enabled."""
    def __init__(self, name: str):
        self.name = name

    def span(self, **kwargs):
        return MockSpan()

    def generation(self, **kwargs):
        return MockSpan()

    def update(self, **kwargs):
        pass


class MockSpan:
    def end(self, **kwargs):
        pass


tracer = ObservabilityTracer()
