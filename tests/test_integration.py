"""Integration tests for end-to-end workflows."""

import pytest
import asyncio
from unittest.mock import patch, MagicMock
from datetime import datetime
import json

from src.models import User, Job, Record, Company
from src.api.auth import create_access_token
from src.worker.tasks import process_enrichment_job
from tests.factories import UserFactory, JobFactory, RecordFactory, CompanyFactory


class TestEndToEndEnrichmentFlow:
    """Test complete enrichment workflow from API to completion."""

    @pytest.mark.asyncio
    async def test_complete_enrichment_workflow(self, client, db_session, mock_gemini):
        """Test full workflow: create job -> upload records -> enrich -> export."""
        # Step 1: Create user and authenticate
        user = UserFactory()
        db_session.add(user)
        db_session.commit()

        token = create_access_token(data={"sub": user.email})
        headers = {"Authorization": f"Bearer {token}"}

        # Step 2: Create enrichment job
        job_data = {
            "name": "E2E Test Job",
            "description": "End-to-end integration test"
        }

        with patch("src.api.routers.jobs.get_current_user", return_value=user):
            response = client.post("/api/v1/jobs/", json=job_data, headers=headers)

        assert response.status_code == 201
        job = response.json()
        job_id = job["id"]

        # Step 3: Upload records
        records_data = [
            {
                "company_name": "Tech Startup Inc",
                "email": "info@techstartup.com",
                "website": "https://techstartup.com"
            },
            {
                "company_name": "Enterprise Corp",
                "email": "contact@enterprise.com",
                "website": "https://enterprise.com"
            },
            {
                "company_name": "Innovation Labs",
                "email": "hello@innovationlabs.io",
                "website": "https://innovationlabs.io"
            }
        ]

        with patch("src.api.routers.records.get_current_user", return_value=user):
            response = client.post(
                f"/api/v1/jobs/{job_id}/records/bulk",
                json=records_data,
                headers=headers
            )

        assert response.status_code == 201
        records = response.json()
        assert len(records) == 3

        # Step 4: Start enrichment
        with patch("src.api.routers.jobs.get_current_user", return_value=user):
            response = client.post(f"/api/v1/jobs/{job_id}/enrich", headers=headers)

        assert response.status_code == 200

        # Step 5: Process enrichment (simulate worker)
        with patch("src.worker.tasks.get_db") as mock_get_db:
            mock_get_db.return_value.__enter__.return_value = db_session
            await process_enrichment_job(job_id)

        # Step 6: Check job completion
        with patch("src.api.routers.jobs.get_current_user", return_value=user):
            response = client.get(f"/api/v1/jobs/{job_id}", headers=headers)

        assert response.status_code == 200
        completed_job = response.json()
        assert completed_job["status"] == "completed"
        assert completed_job["successful_records"] == 3

        # Step 7: Export results
        with patch("src.api.routers.records.get_current_user", return_value=user):
            response = client.get(
                f"/api/v1/jobs/{job_id}/records/export?format=json",
                headers=headers
            )

        assert response.status_code == 200
        export_data = response.json()
        assert len(export_data) == 3
        assert all(record["status"] == "enriched" for record in export_data)


class TestAPIAuthenticationFlow:
    """Test authentication and authorization flows."""

    def test_user_registration_and_login(self, client, db_session):
        """Test user registration and login flow."""
        # Step 1: Register new user
        registration_data = {
            "email": "newuser@example.com",
            "password": "SecurePassword123!",
            "full_name": "New User"
        }

        response = client.post("/api/v1/auth/register", json=registration_data)
        assert response.status_code == 201
        user_data = response.json()
        assert user_data["email"] == "newuser@example.com"

        # Step 2: Login with credentials
        login_data = {
            "username": "newuser@example.com",
            "password": "SecurePassword123!"
        }

        response = client.post("/api/v1/auth/token", data=login_data)
        assert response.status_code == 200
        token_data = response.json()
        assert "access_token" in token_data
        assert token_data["token_type"] == "bearer"

        # Step 3: Access protected endpoint
        headers = {"Authorization": f"Bearer {token_data['access_token']}"}

        with patch("src.api.routers.users.get_current_user") as mock_get_user:
            # Mock the user lookup
            user = db_session.query(User).filter_by(email="newuser@example.com").first()
            mock_get_user.return_value = user

            response = client.get("/api/v1/users/me", headers=headers)

        assert response.status_code == 200
        me_data = response.json()
        assert me_data["email"] == "newuser@example.com"

    def test_unauthorized_access(self, client):
        """Test that unauthorized requests are rejected."""
        # Try to access protected endpoint without token
        response = client.get("/api/v1/jobs/")
        assert response.status_code == 401

        # Try with invalid token
        headers = {"Authorization": "Bearer invalid-token"}
        response = client.get("/api/v1/jobs/", headers=headers)
        assert response.status_code == 401


class TestDataConsistency:
    """Test data consistency across operations."""

    def test_cascade_delete_job(self, db_session):
        """Test that deleting a job cascades to records."""
        # Create job with records
        user = UserFactory()
        job = JobFactory(user=user)
        records = [RecordFactory(job=job) for _ in range(5)]

        db_session.add_all([user, job] + records)
        db_session.commit()

        job_id = job.id
        record_ids = [r.id for r in records]

        # Delete the job
        db_session.delete(job)
        db_session.commit()

        # Verify job is deleted
        assert db_session.query(Job).filter_by(id=job_id).first() is None

        # Verify all records are deleted
        for record_id in record_ids:
            assert db_session.query(Record).filter_by(id=record_id).first() is None

    def test_company_deduplication(self, db_session):
        """Test that companies are deduplicated by domain."""
        # Create first company
        company1 = CompanyFactory(domain="example.com")
        db_session.add(company1)
        db_session.commit()

        # Try to create duplicate
        company2 = Company(
            name="Different Name",
            domain="example.com",
            industry="Different Industry"
        )

        db_session.add(company2)
        with pytest.raises(Exception):  # Should raise integrity error
            db_session.commit()

        db_session.rollback()

        # Verify only one company exists
        companies = db_session.query(Company).filter_by(domain="example.com").all()
        assert len(companies) == 1


class TestConcurrentOperations:
    """Test concurrent operations and race conditions."""

    @pytest.mark.asyncio
    async def test_concurrent_job_processing(self, db_session, mock_gemini):
        """Test processing multiple jobs concurrently."""
        # Create multiple users with jobs
        users_and_jobs = []
        for i in range(3):
            user = UserFactory()
            job = JobFactory(user=user, name=f"Concurrent Job {i}")
            records = [RecordFactory(job=job) for _ in range(10)]

            db_session.add_all([user, job] + records)
            users_and_jobs.append((user, job))

        db_session.commit()

        # Process all jobs concurrently
        with patch("src.worker.tasks.get_db") as mock_get_db:
            mock_get_db.return_value.__enter__.return_value = db_session

            tasks = [
                process_enrichment_job(job.id)
                for _, job in users_and_jobs
            ]

            await asyncio.gather(*tasks)

        # Verify all jobs completed successfully
        for _, job in users_and_jobs:
            db_session.refresh(job)
            assert job.status == "completed"
            assert job.processed_records == 10
            assert job.successful_records == 10


class TestErrorRecovery:
    """Test error handling and recovery scenarios."""

    @pytest.mark.asyncio
    async def test_partial_enrichment_failure(self, db_session, sample_job):
        """Test handling partial failures during enrichment."""
        # Create records
        records = [RecordFactory(job=sample_job) for _ in range(10)]
        db_session.add_all(records)
        db_session.commit()

        # Mock enrichment to fail for some records
        fail_indices = {2, 5, 8}  # Fail for these record indices

        async def mock_enrich_record(record, db):
            index = records.index(record)
            if index in fail_indices:
                record.status = "failed"
                record.error_message = "Simulated failure"
                return False
            else:
                record.status = "enriched"
                record.enriched_data = {"industry": "Technology"}
                return True

        with patch("src.worker.tasks.enrich_single_record", side_effect=mock_enrich_record):
            with patch("src.worker.tasks.get_db") as mock_get_db:
                mock_get_db.return_value.__enter__.return_value = db_session

                await process_enrichment_job(sample_job.id)

        # Verify job completed with partial failures
        db_session.refresh(sample_job)
        assert sample_job.status == "completed"
        assert sample_job.successful_records == 7
        assert sample_job.failed_records == 3

        # Verify individual record statuses
        for i, record in enumerate(records):
            db_session.refresh(record)
            if i in fail_indices:
                assert record.status == "failed"
                assert record.error_message is not None
            else:
                assert record.status == "enriched"
                assert record.enriched_data is not None


class TestPerformanceAndScaling:
    """Test performance with larger datasets."""

    @pytest.mark.asyncio
    async def test_large_batch_processing(self, db_session, mock_gemini):
        """Test processing large batches of records."""
        # Create job with many records
        user = UserFactory()
        job = JobFactory(user=user, name="Large Batch Test")

        # Create 100 records in batches
        batch_size = 20
        for i in range(0, 100, batch_size):
            records = [RecordFactory(job=job) for _ in range(batch_size)]
            db_session.add_all(records)

        db_session.add_all([user, job])
        db_session.commit()

        start_time = datetime.utcnow()

        # Process the job
        with patch("src.worker.tasks.get_db") as mock_get_db:
            mock_get_db.return_value.__enter__.return_value = db_session

            # Use limited concurrency
            with patch("src.worker.tasks.CONCURRENT_LIMIT", 5):
                await process_enrichment_job(job.id)

        end_time = datetime.utcnow()
        processing_time = (end_time - start_time).total_seconds()

        # Verify completion
        db_session.refresh(job)
        assert job.status == "completed"
        assert job.processed_records == 100
        assert job.successful_records == 100

        # Performance assertion (should complete reasonably fast with mocks)
        assert processing_time < 10  # Should complete in under 10 seconds
