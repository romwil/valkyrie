"""Unit tests for LLM processors."""

import pytest
from unittest.mock import patch, MagicMock
import json

from src.processors.llm_processor import (
    LLMProcessor,
    GeminiEnrichmentProcessor,
    parse_llm_response,
    validate_enrichment_data
)
from src.models import Record
from tests.factories import RecordFactory


class TestLLMProcessor:
    """Test base LLM processor functionality."""

    def test_processor_initialization(self, mock_gemini):
        """Test LLM processor initialization."""
        processor = LLMProcessor(api_key="test-key")
        assert processor.api_key == "test-key"
        assert processor.model_name is not None

    def test_format_prompt(self):
        """Test prompt formatting."""
        processor = LLMProcessor(api_key="test-key")

        company_data = {
            "name": "Tech Corp",
            "website": "https://techcorp.com",
            "email": "info@techcorp.com"
        }

        prompt = processor.format_prompt(company_data)
        assert "Tech Corp" in prompt
        assert "techcorp.com" in prompt
        assert isinstance(prompt, str)

    @patch("google.generativeai.GenerativeModel")
    def test_generate_content(self, mock_model):
        """Test content generation with Gemini API."""
        # Mock the response
        mock_response = MagicMock()
        mock_response.text = json.dumps({
            "industry": "Technology",
            "size": "100-500",
            "revenue": "$10M-$50M"
        })
        mock_model.return_value.generate_content.return_value = mock_response

        processor = LLMProcessor(api_key="test-key")
        result = processor.generate_content("Test prompt")

        assert result is not None
        assert "industry" in result
        assert result["industry"] == "Technology"


class TestGeminiEnrichmentProcessor:
    """Test Gemini enrichment processor."""

    def test_enrich_company(self, mock_gemini):
        """Test company enrichment process."""
        processor = GeminiEnrichmentProcessor(api_key="test-key")

        company_data = {
            "name": "Example Corp",
            "website": "https://example.com",
            "email": "contact@example.com",
            "phone": "+1-555-0123"
        }

        # Mock the Gemini response
        expected_enrichment = {
            "industry": "Software",
            "size": "50-200",
            "revenue": "$5M-$25M",
            "description": "A leading software company",
            "key_products": ["SaaS Platform", "API Services"],
            "target_market": "B2B Enterprise",
            "competitors": ["Competitor A", "Competitor B"],
            "founded_year": 2015,
            "headquarters": "San Francisco, CA",
            "employee_growth": "25% YoY"
        }

        with patch.object(processor, "generate_content", return_value=expected_enrichment):
            result = processor.enrich_company(company_data)

        assert result == expected_enrichment
        assert result["industry"] == "Software"
        assert len(result["key_products"]) == 2

    def test_enrich_company_with_minimal_data(self, mock_gemini):
        """Test enrichment with minimal company data."""
        processor = GeminiEnrichmentProcessor(api_key="test-key")

        company_data = {
            "name": "Minimal Corp"
        }

        with patch.object(processor, "generate_content") as mock_generate:
            mock_generate.return_value = {"industry": "Unknown"}
            result = processor.enrich_company(company_data)

        assert result is not None
        # Verify the prompt was called even with minimal data
        mock_generate.assert_called_once()

    def test_handle_api_error(self, mock_gemini):
        """Test handling of API errors."""
        processor = GeminiEnrichmentProcessor(api_key="test-key")

        with patch.object(processor, "generate_content") as mock_generate:
            mock_generate.side_effect = Exception("API rate limit exceeded")

            with pytest.raises(Exception) as exc_info:
                processor.enrich_company({"name": "Test Corp"})

            assert "rate limit" in str(exc_info.value)

    def test_retry_logic(self, mock_gemini):
        """Test retry logic for transient failures."""
        processor = GeminiEnrichmentProcessor(api_key="test-key")

        # Mock to fail twice then succeed
        call_count = 0
        def mock_generate(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("Temporary failure")
            return {"industry": "Technology"}

        with patch.object(processor, "generate_content", side_effect=mock_generate):
            with patch("time.sleep"):  # Don't actually sleep in tests
                result = processor.enrich_company({"name": "Test Corp"}, max_retries=3)

        assert result["industry"] == "Technology"
        assert call_count == 3


class TestResponseParsing:
    """Test LLM response parsing utilities."""

    def test_parse_valid_json_response(self):
        """Test parsing valid JSON response."""
        response_text = '''
        {
            "industry": "Technology",
            "size": "100-500",
            "revenue": "$10M-$50M",
            "description": "A tech company"
        }
        '''

        result = parse_llm_response(response_text)
        assert result["industry"] == "Technology"
        assert result["size"] == "100-500"

    def test_parse_response_with_markdown(self):
        """Test parsing response with markdown formatting."""
        response_text = '''
        Here's the company information:

        ```json
        {
            "industry": "Healthcare",
            "size": "50-200"
        }
        ```

        Additional notes...
        '''

        result = parse_llm_response(response_text)
        assert result["industry"] == "Healthcare"
        assert result["size"] == "50-200"

    def test_parse_invalid_json(self):
        """Test handling of invalid JSON."""
        response_text = "This is not JSON"

        with pytest.raises(ValueError) as exc_info:
            parse_llm_response(response_text)

        assert "Invalid JSON" in str(exc_info.value)

    def test_parse_partial_json(self):
        """Test parsing partially valid JSON."""
        response_text = '''
        {
            "industry": "Technology",
            "size": "100-500",
            "revenue":
        '''

        with pytest.raises(ValueError):
            parse_llm_response(response_text)


class TestDataValidation:
    """Test enrichment data validation."""

    def test_validate_complete_enrichment_data(self):
        """Test validation of complete enrichment data."""
        data = {
            "industry": "Technology",
            "size": "100-500",
            "revenue": "$10M-$50M",
            "description": "A leading tech company",
            "key_products": ["Product A", "Product B"],
            "target_market": "B2B",
            "competitors": ["Comp A", "Comp B"]
        }

        is_valid, errors = validate_enrichment_data(data)
        assert is_valid is True
        assert len(errors) == 0

    def test_validate_missing_required_fields(self):
        """Test validation with missing required fields."""
        data = {
            "size": "100-500",
            "revenue": "$10M-$50M"
        }

        is_valid, errors = validate_enrichment_data(data)
        assert is_valid is False
        assert "industry" in errors

    def test_validate_invalid_field_types(self):
        """Test validation with invalid field types."""
        data = {
            "industry": "Technology",
            "size": "100-500",
            "revenue": "$10M-$50M",
            "key_products": "Should be a list",  # Invalid: should be list
            "founded_year": "2020"  # Invalid: should be int
        }

        is_valid, errors = validate_enrichment_data(data)
        assert is_valid is False
        assert "key_products" in errors
        assert "founded_year" in errors

    def test_validate_empty_data(self):
        """Test validation of empty data."""
        data = {}

        is_valid, errors = validate_enrichment_data(data)
        assert is_valid is False
        assert len(errors) > 0


class TestEnrichmentIntegration:
    """Test full enrichment integration."""

    @pytest.mark.asyncio
    async def test_enrich_record_integration(self, db_session, sample_job, mock_gemini):
        """Test enriching a record through the full pipeline."""
        # Create a record
        record = RecordFactory(
            job=sample_job,
            company_name="Integration Test Corp",
            website="https://integrationtest.com"
        )
        db_session.add(record)
        db_session.commit()

        # Mock enrichment response
        enrichment_data = {
            "industry": "Technology",
            "size": "100-500",
            "revenue": "$10M-$50M",
            "description": "An integration test company",
            "key_products": ["Test Product"],
            "target_market": "Testing Market"
        }

        processor = GeminiEnrichmentProcessor(api_key="test-key")

        with patch.object(processor, "generate_content", return_value=enrichment_data):
            # Enrich the record
            result = await processor.enrich_record(record)

        assert result is True
        assert record.status == "enriched"
        assert record.enriched_data == enrichment_data
        assert record.enriched_data["industry"] == "Technology"
