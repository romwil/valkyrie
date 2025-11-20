"""Valkyrie Worker Service - Celery-based async task processing for LLM data enrichment."""

from .main import app
from .tasks import (
    enrich_sales_data,
    process_batch,
    priority_enrichment,
    health_check
)
from .processors import (
    GeminiProcessor,
    EnrichmentProcessor,
    BatchProcessor
)

__version__ = "1.0.0"
__all__ = [
    "app",
    "enrich_sales_data",
    "process_batch",
    "priority_enrichment",
    "health_check",
    "GeminiProcessor",
    "EnrichmentProcessor",
    "BatchProcessor",
]
