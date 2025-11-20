"""Data enrichment processors using Google Gemini for Valkyrie Worker Service."""

import os
import json
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import google.generativeai as genai
from tenacity import retry, stop_after_attempt, wait_exponential
import asyncio
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)


class GeminiProcessor:
    """Processor for interacting with Google Gemini API."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize Gemini processor with configuration.

        Args:
            config: Optional configuration overrides
        """
        self.config = config or {}
        self.api_key = os.getenv('GEMINI_API_KEY')
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY environment variable not set")

        # Configure Gemini
        genai.configure(api_key=self.api_key)

        # Model configuration
        self.model_name = self.config.get('model', 'gemini-pro')
        self.temperature = self.config.get('temperature', 0.7)
        self.max_tokens = self.config.get('max_tokens', 2048)

        # Initialize model
        self.model = genai.GenerativeModel(self.model_name)

        # Thread pool for concurrent processing
        self.executor = ThreadPoolExecutor(max_workers=5)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    def generate_enrichment(self, data: Dict[str, Any], prompt_template: str) -> Dict[str, Any]:
        """Generate enrichment data using Gemini.

        Args:
            data: Original data to enrich
            prompt_template: Template for the enrichment prompt

        Returns:
            Enriched data dictionary
        """
        try:
            # Format prompt with data
            prompt = prompt_template.format(**data)

            # Generate response
            response = self.model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=self.temperature,
                    max_output_tokens=self.max_tokens,
                )
            )

            # Parse response
            enriched_data = self._parse_response(response.text)
            return enriched_data

        except Exception as e:
            logger.error(f"Gemini generation failed: {str(e)}")
            raise

    def _parse_response(self, response_text: str) -> Dict[str, Any]:
        """Parse Gemini response into structured data.

        Args:
            response_text: Raw response from Gemini

        Returns:
            Parsed data dictionary
        """
        try:
            # Try to parse as JSON first
            if response_text.strip().startswith('{'):
                return json.loads(response_text)

            # Otherwise, structure the response
            lines = response_text.strip().split('\n')
            result = {}

            for line in lines:
                if ':' in line:
                    key, value = line.split(':', 1)
                    result[key.strip()] = value.strip()

            return result if result else {'raw_response': response_text}

        except Exception as e:
            logger.warning(f"Failed to parse response: {str(e)}")
            return {'raw_response': response_text}


class EnrichmentProcessor:
    """Main processor for data enrichment workflows."""

    def __init__(self, gemini_processor: GeminiProcessor):
        """Initialize enrichment processor.

        Args:
            gemini_processor: Configured Gemini processor instance
        """
        self.gemini = gemini_processor
        self.enrichment_templates = self._load_templates()

    def _load_templates(self) -> Dict[str, str]:
        """Load enrichment prompt templates.

        Returns:
            Dictionary of prompt templates
        """
        return {
            'sales_analysis': """Analyze the following sales data and provide enriched insights:

Company: {company_name}
Product: {product_name}
Revenue: ${revenue}
Units Sold: {units_sold}
Region: {region}
Period: {period}

Provide the following enrichments in JSON format:
1. Market position analysis
2. Growth potential score (1-10)
3. Risk factors
4. Recommended actions
5. Competitive landscape insights
6. Seasonal trends
7. Customer segment analysis""",
            'customer_insights': """Analyze customer data for enrichment:

Customer ID: {customer_id}
Purchase History: {purchase_history}
Engagement Score: {engagement_score}
Last Activity: {last_activity}

Provide enriched customer insights in JSON format:
1. Customer lifetime value prediction
2. Churn risk assessment
3. Upsell opportunities
4. Preferred communication channels
5. Product recommendations""",
            'market_intelligence': """Enrich market data with intelligence:

Industry: {industry}
Market Size: ${market_size}
Growth Rate: {growth_rate}%
Key Players: {key_players}

Provide market intelligence in JSON format:
1. Market trends and forecasts
2. Emerging opportunities
3. Threat analysis
4. Innovation indicators
5. Regulatory considerations"""
        }

    def enrich_record(self, record_data: Dict[str, Any], priority: bool = False) -> Dict[str, Any]:
        """Enrich a single record with AI-generated insights.

        Args:
            record_data: Original record data
            priority: Whether this is a priority enrichment

        Returns:
            Enriched data dictionary
        """
        try:
            # Determine record type and select template
            record_type = record_data.get('type', 'sales_analysis')
            template = self.enrichment_templates.get(
                record_type, 
                self.enrichment_templates['sales_analysis']
            )

            # Generate enrichment
            enriched = self.gemini.generate_enrichment(record_data, template)

            # Add metadata
            enriched['_enrichment_metadata'] = {
                'timestamp': datetime.utcnow().isoformat(),
                'model': self.gemini.model_name,
                'priority': priority,
                'record_type': record_type
            }

            # Merge with original data
            result = {**record_data, **enriched}

            return result

        except Exception as e:
            logger.error(f"Record enrichment failed: {str(e)}")
            raise

    def enrich_batch(self, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Enrich multiple records concurrently.

        Args:
            records: List of records to enrich

        Returns:
            List of enriched records
        """
        enriched_records = []

        # Process in parallel using thread pool
        futures = []
        for record in records:
            future = self.gemini.executor.submit(self.enrich_record, record)
            futures.append(future)

        # Collect results
        for future in futures:
            try:
                result = future.result(timeout=30)
                enriched_records.append(result)
            except Exception as e:
                logger.error(f"Batch enrichment error: {str(e)}")
                enriched_records.append({
                    **record,
                    '_error': str(e)
                })

        return enriched_records


class BatchProcessor:
    """Processor for handling batch operations."""

    def __init__(self, batch_size: int = 100):
        """Initialize batch processor.

        Args:
            batch_size: Default batch size for processing
        """
        self.batch_size = batch_size
        self.stats = {
            'total_processed': 0,
            'total_errors': 0,
            'processing_time': 0
        }

    def process_batch(self, task_instance, job_id: int, record_ids: List[int]) -> Dict[str, Any]:
        """Process a batch of records.

        Args:
            task_instance: Celery task instance
            job_id: Job ID being processed
            record_ids: List of record IDs to process

        Returns:
            Batch processing results
        """
        start_time = datetime.utcnow()

        try:
            # Delegate to the enrichment task
            from .tasks import enrich_sales_data
            result = enrich_sales_data.apply_async(
                args=[job_id, record_ids],
                queue='enrichment'
            ).get(timeout=300)

            # Update stats
            self.stats['total_processed'] += result.get('processed', 0)
            self.stats['total_errors'] += result.get('errors', 0)

            # Calculate processing time
            end_time = datetime.utcnow()
            processing_time = (end_time - start_time).total_seconds()
            self.stats['processing_time'] += processing_time

            return {
                'job_id': job_id,
                'batch_size': len(record_ids),
                'processed': result.get('processed', 0),
                'errors': result.get('errors', 0),
                'processing_time': processing_time,
                'stats': self.stats
            }

        except Exception as e:
            logger.error(f"Batch processing failed: {str(e)}")
            raise

    def get_stats(self) -> Dict[str, Any]:
        """Get current batch processing statistics.

        Returns:
            Current statistics dictionary
        """
        return self.stats.copy()

    def reset_stats(self):
        """Reset batch processing statistics."""
        self.stats = {
            'total_processed': 0,
            'total_errors': 0,
            'processing_time': 0
        }
