"""Unit tests for Records API endpoints."""

import pytest
from unittest.mock import patch

from src.models import Record
from tests.factories import RecordFactory


class TestRecordsAPI:
    """Test records API endpoints."""

    def test_create_records_bulk(self, client, db_session, sample_user, sample_job, auth_headers):
        """Test bulk record creation."""
        records_data = [
            {
                "company_name": "Company A",
                "email": "contact@companya.com",
                "phone": "+1-555-0001",
                "website": "https://companya.com"
            },
            {
                "company_name": "Company B",
                "email": "info@companyb.com",
                "phone": "+1-555-0002",
                "website": "https://companyb.com"
            }
        ]

        with patch("src.api.routers.records.get_current_user", return_value=sample_user):
            response = client.post(
                f"/api/v1/jobs/{sample_job.id}/records/bulk",
                json=records_data,
                headers=auth_headers
            )

        assert response.status_code == 201
        data = response.json()
        assert len(data) == 2
        assert data[0]["company_name"] == "Company A"
        assert data[1]["company_name"] == "Company B"

    def test_list_job_records(self, client, db_session, sample_user, sample_job, auth_headers):
        """Test listing records for a job."""
        # Create records
        records = [RecordFactory(job=sample_job) for _ in range(15)]
        db_session.add_all(records)
        db_session.commit()

        with patch("src.api.routers.records.get_current_user", return_value=sample_user):
            response = client.get(
                f"/api/v1/jobs/{sample_job.id}/records",
                headers=auth_headers
            )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 15
        assert all(record["job_id"] == sample_job.id for record in data)

    def test_get_record_by_id(self, client, db_session, sample_user, sample_job, auth_headers):
        """Test getting a specific record."""
        record = RecordFactory(job=sample_job)
        db_session.add(record)
        db_session.commit()

        with patch("src.api.routers.records.get_current_user", return_value=sample_user):
            response = client.get(
                f"/api/v1/records/{record.id}",
                headers=auth_headers
            )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == record.id
        assert data["company_name"] == record.company_name

    def test_update_record_enrichment(self, client, db_session, sample_user, sample_job, auth_headers):
        """Test updating record with enrichment data."""
        record = RecordFactory(job=sample_job)
        db_session.add(record)
        db_session.commit()

        enrichment_data = {
            "status": "enriched",
            "enriched_data": {
                "industry": "Technology",
                "size": "50-200",
                "revenue": "$10M-$50M",
                "description": "A technology company"
            }
        }

        with patch("src.api.routers.records.get_current_user", return_value=sample_user):
            response = client.patch(
                f"/api/v1/records/{record.id}",
                json=enrichment_data,
                headers=auth_headers
            )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "enriched"
        assert data["enriched_data"]["industry"] == "Technology"

    def test_filter_records_by_status(self, client, db_session, sample_user, sample_job, auth_headers):
        """Test filtering records by status."""
        # Create records with different statuses
        pending_records = [RecordFactory(job=sample_job, status="pending") for _ in range(5)]
        enriched_records = [RecordFactory(job=sample_job, set_enriched_status="enriched") for _ in range(3)]
        failed_records = [RecordFactory(job=sample_job, set_failed_status="failed") for _ in range(2)]

        db_session.add_all(pending_records + enriched_records + failed_records)
        db_session.commit()

        with patch("src.api.routers.records.get_current_user", return_value=sample_user):
            # Filter by pending
            response = client.get(
                f"/api/v1/jobs/{sample_job.id}/records?status=pending",
                headers=auth_headers
            )
            assert response.status_code == 200
            assert len(response.json()) == 5

            # Filter by enriched
            response = client.get(
                f"/api/v1/jobs/{sample_job.id}/records?status=enriched",
                headers=auth_headers
            )
            assert response.status_code == 200
            assert len(response.json()) == 3

            # Filter by failed
            response = client.get(
                f"/api/v1/jobs/{sample_job.id}/records?status=failed",
                headers=auth_headers
            )
            assert response.status_code == 200
            assert len(response.json()) == 2

    def test_delete_record(self, client, db_session, sample_user, sample_job, auth_headers):
        """Test deleting a record."""
        record = RecordFactory(job=sample_job)
        db_session.add(record)
        db_session.commit()

        with patch("src.api.routers.records.get_current_user", return_value=sample_user):
            response = client.delete(f"/api/v1/records/{record.id}", headers=auth_headers)

        assert response.status_code == 204
        assert db_session.query(Record).filter_by(id=record.id).first() is None

    def test_batch_update_records(self, client, db_session, sample_user, sample_job, auth_headers):
        """Test batch updating multiple records."""
        records = [RecordFactory(job=sample_job) for _ in range(3)]
        db_session.add_all(records)
        db_session.commit()

        update_data = {
            "record_ids": [r.id for r in records],
            "status": "processing"
        }

        with patch("src.api.routers.records.get_current_user", return_value=sample_user):
            response = client.patch(
                f"/api/v1/jobs/{sample_job.id}/records/batch",
                json=update_data,
                headers=auth_headers
            )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3
        assert all(record["status"] == "processing" for record in data)

    def test_export_records(self, client, db_session, sample_user, sample_job, auth_headers):
        """Test exporting records to CSV."""
        # Create some enriched records
        records = [
            RecordFactory(job=sample_job, set_enriched_status="enriched") 
            for _ in range(5)
        ]
        db_session.add_all(records)
        db_session.commit()

        with patch("src.api.routers.records.get_current_user", return_value=sample_user):
            response = client.get(
                f"/api/v1/jobs/{sample_job.id}/records/export?format=csv",
                headers=auth_headers
            )

        assert response.status_code == 200
        assert response.headers["content-type"] == "text/csv; charset=utf-8"
        assert "attachment" in response.headers.get("content-disposition", "")

    def test_record_pagination(self, client, db_session, sample_user, sample_job, auth_headers):
        """Test record listing pagination."""
        # Create many records
        records = [RecordFactory(job=sample_job) for _ in range(50)]
        db_session.add_all(records)
        db_session.commit()

        with patch("src.api.routers.records.get_current_user", return_value=sample_user):
            # First page
            response = client.get(
                f"/api/v1/jobs/{sample_job.id}/records?skip=0&limit=20",
                headers=auth_headers
            )
            assert response.status_code == 200
            assert len(response.json()) == 20

            # Last page
            response = client.get(
                f"/api/v1/jobs/{sample_job.id}/records?skip=40&limit=20",
                headers=auth_headers
            )
            assert response.status_code == 200
            assert len(response.json()) == 10
