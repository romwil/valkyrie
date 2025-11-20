"""LLM service for Gemini integration."""

import os
import json
import logging
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime

import google.generativeai as genai
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from src.models import Record, Company
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# Configure Gemini
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    logger.warning("GEMINI_API_KEY not found in environment variables")
else:
    genai.configure(api_key=GEMINI_API_KEY)


class LLMService:
    """Service for LLM-based enrichment using Google Gemini."""

    def __init__(self, model_name: str = "gemini-pro", temperature: float = 0.7):
        """Initialize LLM service."""
        self.model_name = model_name
        self.temperature = temperature
        self.model = None

        if GEMINI_API_KEY:
            try:
                self.model = genai.GenerativeModel(model_name)
                logger.info(f"Initialized Gemini model: {model_name}")
            except Exception as e:
                logger.error(f"Failed to initialize Gemini model: {e}")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type(Exception)
    )
    async def enrich_company_data(
        self,
        company_name: str,
        existing_data: Optional[Dict[str, Any]] = None,
        enrichment_fields: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Enrich company data using LLM."""
        if not self.model:
            raise ValueError("Gemini model not initialized")

        # Default enrichment fields
        if not enrichment_fields:
            enrichment_fields = [
                "industry",
                "employee_count",
                "revenue_range",
                "headquarters_location",
                "company_description",
                "key_products_services",
                "target_market",
                "competitors"
            ]

        # Build prompt
        prompt = self._build_enrichment_prompt(company_name, existing_data, enrichment_fields)

        try:
            # Generate response
            response = await asyncio.to_thread(
                self.model.generate_content,
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=self.temperature,
                    max_output_tokens=1000
                )
            )

            # Parse response
            enriched_data = self._parse_llm_response(response.text)

            # Validate and clean data
            enriched_data = self._validate_enriched_data(enriched_data, enrichment_fields)

            return {
                "success": True,
                "enriched_data": enriched_data,
                "llm_response": response.text,
                "timestamp": datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"Failed to enrich company data for {company_name}: {e}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }

    def _build_enrichment_prompt(self, company_name: str, existing_data: Optional[Dict[str, Any]], fields: List[str]) -> str:
        """Build prompt for company enrichment."""
        prompt = f"""You are a business data analyst. Provide accurate information about the following company.

Company Name: {company_name}
"""

        if existing_data:
            prompt += f"
Existing Information:
"
            for key, value in existing_data.items():
                if value:
                    prompt += f"- {key}: {value}
"

        prompt += f"""
Please provide the following information in JSON format:
{"""

        field_descriptions = {
            "industry": "Primary industry or sector (e.g., 'Technology', 'Healthcare', 'Finance')",
            "employee_count": "Estimated number of employees (integer)",
            "revenue_range": "Annual revenue range (e.g., '$10M-$50M', '$100M-$500M')",
            "headquarters_location": "City, State/Country of headquarters",
            "company_description": "Brief description of what the company does (2-3 sentences)",
            "key_products_services": "Main products or services offered (list)",
            "target_market": "Primary customer segments or markets",
            "competitors": "Main competitors (list of company names)"
        }

        for i, field in enumerate(fields):
            desc = field_descriptions.get(field, f"Information about {field}")
            prompt += f'
  "{field}": "{desc}"'
            if i < len(fields) - 1:
                prompt += ","

        prompt += """
}

Provide only the JSON response with accurate, factual information. If information is not available for a field, use null."""

        return prompt

    def _parse_llm_response(self, response_text: str) -> Dict[str, Any]:
        """Parse LLM response to extract JSON data."""
        try:
            # Try to extract JSON from response
            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}') + 1

            if start_idx != -1 and end_idx > start_idx:
                json_str = response_text[start_idx:end_idx]
                return json.loads(json_str)
            else:
                # If no JSON found, try to parse the entire response
                return json.loads(response_text)

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}")
            logger.debug(f"Response text: {response_text}")

            # Fallback: try to extract key-value pairs
            data = {}
            lines = response_text.split('
')
            for line in lines:
                if ':' in line:
                    key, value = line.split(':', 1)
                    key = key.strip().lower().replace(' ', '_')
                    value = value.strip()
                    if value and value != 'null':
                        data[key] = value

            return data

    def _validate_enriched_data(self, data: Dict[str, Any], expected_fields: List[str]) -> Dict[str, Any]:
        """Validate and clean enriched data."""
        cleaned_data = {}

        for field in expected_fields:
            if field in data:
                value = data[field]

                # Clean and validate specific fields
                if field == "employee_count":
                    # Try to extract integer from string
                    if isinstance(value, str):
                        try:
                            # Extract number from strings like "1000", "~1000", "1,000"
                            import re
                            numbers = re.findall(r'\d+', value.replace(',', ''))
                            if numbers:
                                value = int(numbers[0])
                        except:
                            value = None
                    elif not isinstance(value, int):
                        value = None

                elif field in ["key_products_services", "competitors"]:
                    # Ensure these are lists
                    if isinstance(value, str):
                        value = [item.strip() for item in value.split(',')]
                    elif not isinstance(value, list):
                        value = [str(value)] if value else []

                elif field == "revenue_range":
                    # Standardize revenue format
                    if value and isinstance(value, str):
                        value = value.strip()
                        if not value.startswith('$'):
                            value = f"${value}"

                cleaned_data[field] = value

        return cleaned_data

    async def resolve_company_title(
        self,
        company_name: str,
        additional_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Resolve and standardize company name/title."""
        if not self.model:
            raise ValueError("Gemini model not initialized")

        prompt = f"""You are a company name standardization expert. Given the following company name and context, provide the official company name.

Input Company Name: {company_name}
"""

        if additional_context:
            prompt += f"
Additional Context:
"
            for key, value in additional_context.items():
                if value:
                    prompt += f"- {key}: {value}
"

        prompt += """
Provide the response in JSON format:
{
  "official_name": "The official registered company name",
  "common_name": "The commonly used name",
  "aliases": ["List of alternative names or abbreviations"],
  "confidence": 0.95
}

Respond only with the JSON."""

        try:
            response = await asyncio.to_thread(
                self.model.generate_content,
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.3,  # Lower temperature for more consistent results
                    max_output_tokens=200
                )
            )

            result = self._parse_llm_response(response.text)
            return {
                "success": True,
                "resolved_data": result,
                "original_name": company_name,
                "timestamp": datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"Failed to resolve company title for {company_name}: {e}")
            return {
                "success": False,
                "error": str(e),
                "original_name": company_name,
                "timestamp": datetime.utcnow().isoformat()
            }

    async def batch_enrich_records(
        self,
        records: List[Record],
        session: Session,
        batch_size: int = 10
    ) -> Dict[str, Any]:
        """Enrich multiple records in batches."""
        total_records = len(records)
        successful = 0
        failed = 0

        for i in range(0, total_records, batch_size):
            batch = records[i:i + batch_size]

            # Process batch concurrently
            tasks = []
            for record in batch:
                if record.company:
                    task = self.enrich_company_data(
                        record.company.name,
                        record.original_data
                    )
                    tasks.append((record, task))

            # Wait for all tasks in batch
            for record, task in tasks:
                try:
                    result = await task

                    if result["success"]:
                        # Update record
                        record.mark_processed(
                            enriched_data=result["enriched_data"],
                            llm_response=result
                        )

                        # Update company enrichment data
                        if record.company:
                            record.company.merge_enrichment_data(result["enriched_data"])

                        successful += 1
                    else:
                        record.mark_failed(result.get("error", "Unknown error"))
                        failed += 1

                except Exception as e:
                    logger.error(f"Failed to process record {record.id}: {e}")
                    record.mark_failed(str(e))
                    failed += 1

            # Commit batch
            session.commit()

            # Log progress
            processed = i + len(batch)
            logger.info(f"Processed {processed}/{total_records} records")

        return {
            "total_records": total_records,
            "successful": successful,
            "failed": failed,
            "success_rate": round((successful / total_records * 100) if total_records > 0 else 0, 2)
        }
