import logging
import os
from typing import Optional

logger = logging.getLogger("sanket.observability")

def setup_phoenix() -> bool:
    """
    Set up Arize Phoenix OpenTelemetry tracing for LangChain.
    """
    try:
        from opentelemetry import trace
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        import phoenix as px
        from openinference.instrumentation.langchain import LangChainInstrumentor
        
        phoenix_endpoint = os.getenv(
            "PHOENIX_COLLECTOR_ENDPOINT",
            "https://app.phoenix.arize.com"
        )
        phoenix_api_key = os.getenv(
            "PHOENIX_API_KEY", ""
        )
        
        if not phoenix_api_key:
            logger.warning("PHOENIX_API_KEY not set — Arize Phoenix tracing disabled")
            return False
            
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        
        exporter = OTLPSpanExporter(
            endpoint=f"{phoenix_endpoint}/v1/traces",
            headers={"api_key": phoenix_api_key}
        )
        
        provider = TracerProvider()
        provider.add_span_processor(BatchSpanProcessor(exporter))
        trace.set_tracer_provider(provider)
        
        LangChainInstrumentor().instrument()
        
        logger.info("Arize Phoenix tracing enabled")
        return True
        
    except ImportError as e:
        logger.warning(f"Arize packages not installed: {e}")
        return False
    except Exception as e:
        logger.warning(f"Phoenix setup failed: {e}. Continuing without tracing.")
        return False

def get_tracer(name: str):
    """
    Retrieve OpenTelemetry tracer if available.
    """
    try:
        from opentelemetry import trace
        return trace.get_tracer(name)
    except:
        return None

class SanketTracer:
    """
    A simple context manager for tracing when Phoenix/OpenTelemetry is not active.
    """
    def __init__(self, tracer, span_name: str, attributes: dict = None):
        self.tracer = tracer
        self.span_name = span_name
        self.attributes = attributes or {}
        self.span = None
        
    def __enter__(self):
        if self.tracer:
            try:
                self.span = self.tracer.start_span(self.span_name)
                for key, value in self.attributes.items():
                    self.span.set_attribute(key, str(value))
            except:
                pass
        return self
        
    def __exit__(self, *args):
        if self.span:
            try:
                self.span.end()
            except:
                pass
