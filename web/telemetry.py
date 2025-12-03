import os
import socket
import uuid
from typing import Optional

from opentelemetry import metrics, trace
from opentelemetry.exporter.cloud_trace import CloudTraceSpanExporter
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.instrumentation.psycopg2 import Psycopg2Instrumentor
from opentelemetry.propagate import set_global_textmap
from opentelemetry.propagators.cloud_trace_propagator import (
    CloudTraceFormatPropagator,
)
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor


_initialized = False


def _build_resource() -> Resource:
    service_name = os.environ.get("SERVICE_NAME", "ctgov-compliance-web")
    service_namespace = os.environ.get("SERVICE_NAMESPACE", "ctgov")
    # Prevents metric conflicts when instances restart or scale
    instance_id = os.environ.get("SERVICE_INSTANCE_ID") or f"{socket.gethostname()}-{uuid.uuid4().hex[:8]}"
    return Resource.create(
        {
            "service.name": service_name,
            "service.namespace": service_namespace,
            "service.instance.id": instance_id,
        }
    )


def init_telemetry(enable_metrics: Optional[bool] = None) -> None:
    global _initialized
    if _initialized:
        return

    # Avoid double-initialization under Flask debug reloader: run only in the reloader child
    if os.environ.get("FLASK_DEBUG") in ("1", "true", "True") and os.environ.get("WERKZEUG_RUN_MAIN") != "true":
        _initialized = True
        return

    # Disabled by default; enable via OTEL_ENABLED=true
    otel_enabled = os.environ.get("OTEL_ENABLED", "false").lower() in ("1", "true", "yes")
    if not otel_enabled:
        _initialized = True
        return

    set_global_textmap(CloudTraceFormatPropagator())

    resource = _build_resource()

    tracer_provider = TracerProvider(resource=resource)
    cloud_trace_exporter = CloudTraceSpanExporter()
    tracer_provider.add_span_processor(BatchSpanProcessor(cloud_trace_exporter))
    trace.set_tracer_provider(tracer_provider)

    if enable_metrics is None:
        enable_metrics = os.environ.get("OTEL_METRICS_ENABLED", "false").lower() in ("1", "true", "yes")

    if enable_metrics:
        # Import Cloud Monitoring exporter only when metrics are enabled
        try:
            from opentelemetry.exporter.cloud_monitoring import (
                CloudMonitoringMetricsExporter,
            )

            # Allow tuning the export interval to satisfy Cloud Monitoring sampling constraints
            interval_ms_env = os.environ.get("OTEL_METRIC_EXPORT_INTERVAL_MILLIS") or os.environ.get("OTEL_METRICS_EXPORT_INTERVAL_MILLIS")
            try:
                export_interval_millis = int(interval_ms_env) if interval_ms_env else 60000
            except Exception:
                export_interval_millis = 60000

            meter_provider = MeterProvider(
                metric_readers=[
                    PeriodicExportingMetricReader(
                        CloudMonitoringMetricsExporter(), export_interval_millis=export_interval_millis
                    )
                ],
                resource=resource,
            )
            metrics.set_meter_provider(meter_provider)
        except Exception:
            # Metrics are optional; continue without if exporter not available
            pass

    # Auto-instrument libraries used by the app
    RequestsInstrumentor().instrument()
    try:
        Psycopg2Instrumentor().instrument()
    except Exception:
        # If psycopg2 is not present at import time in some environments, continue
        pass

    _initialized = True


def instrument_flask_app(app) -> None:
    # Instrument a specific Flask app instance
    FlaskInstrumentor().instrument_app(app) 