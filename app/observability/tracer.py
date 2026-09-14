"""Observability layer integrating Langfuse for tracing requests, orchestrator decisions, and tool calls."""

import time
import logging
from typing import Optional, Dict, Any
from contextlib import contextmanager

from app.config.settings import settings

logger = logging.getLogger("financial_agent.tracer")

try:
    from langfuse import Langfuse
except ImportError:
    Langfuse = None


class ObservabilityTracer:
    """Manages Langfuse tracing lifecycle with zero-overhead graceful fallback."""

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
