from __future__ import annotations

import atexit
import logging
from collections.abc import Awaitable, Callable, Sequence
from functools import wraps
from pathlib import Path
from typing import TYPE_CHECKING, ParamSpec, TypeVar, cast
from urllib.parse import urlparse, urlunparse

from fastapi import FastAPI
from opentelemetry import trace

from app.core.config import settings

if TYPE_CHECKING:
    from opentelemetry.sdk.trace.export import SpanExporter

logger = logging.getLogger("app.core.tracing")

_configured = False


def _normalize_otlp_endpoint(endpoint: str) -> str:
    parsed = urlparse(endpoint)
    if parsed.path in ("", "/"):
        return urlunparse(parsed._replace(path="/v1/traces"))
    return endpoint


def get_tracer() -> trace.Tracer:
    return trace.get_tracer(settings.tracing_service_name)


def configure_tracing() -> None:
    """Idempotent. Must run *before* the first SQLAlchemy engine is created."""
    global _configured
    if _configured or not settings.tracing_enabled:
        return

    from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry.sdk.trace.sampling import ParentBased, TraceIdRatioBased

    provider = TracerProvider(
        resource=Resource.create({"service.name": settings.tracing_service_name}),
        sampler=ParentBased(TraceIdRatioBased(settings.tracing_sample_rate)),
    )
    for exporter in _build_exporters():
        provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    SQLAlchemyInstrumentor().instrument()
    _configured = True


def _build_exporters() -> list[SpanExporter]:
    """Choose span destinations from settings (OTLP > file, console as last resort)."""
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    from opentelemetry.sdk.trace import ReadableSpan
    from opentelemetry.sdk.trace.export import (
        ConsoleSpanExporter,
        SpanExporter,
        SpanExportResult,
    )

    class FileSpanExporter(SpanExporter):  # type: ignore[misc]  # optional SDK dep is Any when absent
        """Append one compact JSON span per line to a file (JSON Lines)."""

        def __init__(self, file_path: str | Path) -> None:
            self._path = Path(file_path)
            self._path.parent.mkdir(parents=True, exist_ok=True)

        def export(self, spans: Sequence[ReadableSpan]) -> SpanExportResult:
            if not spans:
                return SpanExportResult.SUCCESS
            lines = "".join(f"{span.to_json(indent=None)}\n" for span in spans)
            try:
                with self._path.open("a", encoding="utf-8") as fh:
                    fh.write(lines)
            except OSError:
                logger.exception("failed to write spans to %s", self._path)
                return SpanExportResult.FAILURE
            return SpanExportResult.SUCCESS

        def shutdown(self) -> None:
            pass

        def force_flush(self, timeout_millis: int = 30_000) -> bool:
            return True

    exporters: list[SpanExporter] = []
    if settings.tracing_otlp_endpoint:
        exporters.append(
            OTLPSpanExporter(endpoint=_normalize_otlp_endpoint(settings.tracing_otlp_endpoint))
        )
    if settings.tracing_log_to_file:
        exporters.append(FileSpanExporter(settings.tracing_log_file))
    if settings.tracing_log_to_console or not exporters:
        exporters.append(ConsoleSpanExporter())
    return exporters


def instrument_app(app: FastAPI) -> None:
    """Instrument a FastAPI app's HTTP layer (call once the app exists)."""
    if settings.tracing_enabled:
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

        FastAPIInstrumentor.instrument_app(app, exclude_spans=["receive", "send"])


P = ParamSpec("P")
R = TypeVar("R")


def traced(name: str) -> Callable[[Callable[P, Awaitable[R]]], Callable[P, Awaitable[R]]]:
    """Decorator that wraps an async function in a span named ``name``."""

    def decorator(func: Callable[P, Awaitable[R]]) -> Callable[P, Awaitable[R]]:
        @wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            with get_tracer().start_as_current_span(name):
                return await func(*args, **kwargs)

        return wrapper

    return decorator


def _shutdown() -> None:
    if _configured:
        from opentelemetry.sdk.trace import TracerProvider

        cast(TracerProvider, trace.get_tracer_provider()).shutdown()


atexit.register(_shutdown)
