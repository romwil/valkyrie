"""Unit tests for Jobs API endpoints."""

import pytest
from datetime import datetime
from unittest.mock import patch, MagicMock

from fastapi.testclient import TestClient
from src.models import User, Job
from tests.factories import UserFactory, JobFactory


class TestJobsAPI:
    """Test jobs API endpoints."""

    def test_create_job(self, client, sample_user, auth_headers):
        """Test creating a new job."""
        job_data = {
            "name": "Test Enrichment Job",
            "total_records": 50
        }

        with patch("src.api.routers.jobs.get_current_user", return_value=sample_user):
            response = client.post("/api/v1/jobs/", json=job_data, headers=auth_headers)

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Test Enrichment Job"
        assert data["status"] == "pending"
        assert data["total_records"] == 50

    def test_list_jobs(self, client, db_session, sample_user, auth_headers):
        """Test listing user's jobs."""
        # Create some jobs
        jobs = [JobFactory(user=sample_user) for _ in range(5)]
        db_session.add_all(jobs)
        db_session.commit()

        with patch("src.api.routers.jobs.get_current_user", return_value=sample_user):
            response = client.get("/api/v1/jobs/", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 5
        assert all(job["user_id"] == sample_user.id for job in data)

    def test_get_job_by_id(self, client, db_session, sample_user, sample_job, auth_headers):
        """Test getting a specific job."""
        with patch("src.api.routers.jobs.get_current_user", return_value=sample_user):
            response = client.get(f"/api/v1/jobs/{sample_job.id}", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == sample_job.id
        assert data["name"] == sample_job.name

    def test_get_job_unauthorized(self, client, db_session, sample_job):
        """Test getting a job without authentication."""
        response = client.get(f"/api/v1/jobs/{sample_job.id}")
        assert response.status_code == 401

    def test_update_job_status(self, client, db_session, sample_user, sample_job, auth_headers):
        """Test updating job status."""
        update_data = {
            "status": "processing",
            "processed_records": 10,
            "successful_records": 8,
            "failed_records": 2
        }

        with patch("src.api.routers.jobs.get_current_user", return_value=sample_user):
            response = client.patch(
                f"/api/v1/jobs/{sample_job.id}",
                json=update_data,
                headers=auth_headers
            )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "processing"
        assert data["processed_records"] == 10

    def test_delete_job(self, client, db_session, sample_user, sample_job, auth_headers):
        """Test deleting a job."""
        with patch("src.api.routers.jobs.get_current_user", return_value=sample_user):
            response = client.delete(f"/api/v1/jobs/{sample_job.id}", headers=auth_headers)

        assert response.status_code == 204
        assert db_session.query(Job).filter_by(id=sample_job.id).first() is None

    def test_job_pagination(self, client, db_session, sample_user, auth_headers):
        """Test job listing pagination."""
        # Create many jobs
        jobs = [JobFactory(user=sample_user) for _ in range(25)]
        db_session.add_all(jobs)
        db_session.commit()

        with patch("src.api.routers.jobs.get_current_user", return_value=sample_user):
            # First page
            response = client.get("/api/v1/jobs/?skip=0&limit=10", headers=auth_headers)
            assert response.status_code == 200
            assert len(response.json()) == 10

            # Second page
            response = client.get("/api/v1/jobs/?skip=10&limit=10", headers=auth_headers)
            assert response.status_code == 200
            assert len(response.json()) == 10

            # Third page (partial)
            response = client.get("/api/v1/jobs/?skip=20&limit=10", headers=auth_headers)
            assert response.status_code == 200
            assert len(response.json()) == 5

    def test_job_filtering_by_status(self, client, db_session, sample_user, auth_headers):
        """Test filtering jobs by status."""
        # Create jobs with different statuses
        pending_jobs = [JobFactory(user=sample_user, status="pending") for _ in range(3)]
        processing_jobs = [JobFactory(user=sample_user, status="processing") for _ in range(2)]
        completed_jobs = [JobFactory(user=sample_user, status="completed") for _ in range(4)]

        db_session.add_all(pending_jobs + processing_jobs + completed_jobs)
        db_session.commit()

        with patch("src.api.routers.jobs.get_current_user", return_value=sample_user):
            # Filter by pending
            response = client.get("/api/v1/jobs/?status=pending", headers=auth_headers)
            assert response.status_code == 200
            assert len(response.json()) == 3

            # Filter by processing
            response = client.get("/api/v1/jobs/?status=processing", headers=auth_headers)
            assert response.status_code == 200
            assert len(response.json()) == 2

            # Filter by completed
            response = client.get("/api/v1/jobs/?status=completed", headers=auth_headers)
            assert response.status_code == 200
            assert len(response.json()) == 4

    def test_job_sorting(self, client, db_session, sample_user, auth_headers):
        """Test sorting jobs by different fields."""
        # Create jobs with different creation times
        old_job = JobFactory(user=sample_user, name="Old Job")
        old_job.created_at = datetime(2023, 1, 1)

        new_job = JobFactory(user=sample_user, name="New Job")
        new_job.created_at = datetime(2023, 12, 31)

        db_session.add_all([old_job, new_job])
        db_session.commit()

        with patch("src.api.routers.jobs.get_current_user", return_value=sample_user):
            # Sort by created_at ascending
            response = client.get("/api/v1/jobs/?sort_by=created_at&order=asc", headers=auth_headers)
            assert response.status_code == 200
            data = response.json()
            assert data[0]["name"] == "Old Job"
            assert data[1]["name"] == "New Job"

            # Sort by created_at descending
            response = client.get("/api/v1/jobs/?sort_by=created_at&order=desc", headers=auth_headers)
            assert response.status_code == 200
            data = response.json()
            assert data[0]["name"] == "New Job"
            assert data[1]["name"] == "Old Job"
