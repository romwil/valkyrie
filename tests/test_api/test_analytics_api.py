"""Unit tests for Analytics API endpoints."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import patch

from tests.factories import JobFactory, RecordFactory, UserFactory


class TestAnalyticsAPI:
    """Test analytics API endpoints."""

    def test_get_job_statistics(self, client, db_session, sample_user, auth_headers):
        """Test getting job statistics."""
        # Create jobs with different statuses
        completed_jobs = [
            JobFactory(
                user=sample_user,
                status="completed",
                total_records=100,
                successful_records=95,
                failed_records=5
            ) for _ in range(3)
        ]
        processing_jobs = [
            JobFactory(
                user=sample_user,
                status="processing",
                total_records=50,
                processed_records=25
            ) for _ in range(2)
        ]

        db_session.add_all(completed_jobs + processing_jobs)
        db_session.commit()

        with patch("src.api.routers.analytics.get_current_user", return_value=sample_user):
            response = client.get("/api/v1/analytics/jobs/statistics", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["total_jobs"] >= 5
        assert data["completed_jobs"] >= 3
        assert data["processing_jobs"] >= 2
        assert data["total_records_processed"] >= 300

    def test_get_enrichment_metrics(self, client, db_session, sample_user, auth_headers):
        """Test getting enrichment metrics."""
        # Create a job with various record statuses
        job = JobFactory(user=sample_user, total_records=100)

        # Create records with different statuses
        enriched_records = [
            RecordFactory(job=job, set_enriched_status="enriched") 
            for _ in range(60)
        ]
        failed_records = [
            RecordFactory(job=job, set_failed_status="failed") 
            for _ in range(10)
        ]
        pending_records = [
            RecordFactory(job=job, status="pending") 
            for _ in range(30)
        ]

        db_session.add_all([job] + enriched_records + failed_records + pending_records)
        db_session.commit()

        with patch("src.api.routers.analytics.get_current_user", return_value=sample_user):
            response = client.get(
                f"/api/v1/analytics/jobs/{job.id}/enrichment-metrics",
                headers=auth_headers
            )

        assert response.status_code == 200
        data = response.json()
        assert data["total_records"] == 100
        assert data["enriched_records"] == 60
        assert data["failed_records"] == 10
        assert data["pending_records"] == 30
        assert data["success_rate"] == 60.0
        assert data["failure_rate"] == 10.0

    def test_get_daily_activity(self, client, db_session, sample_user, auth_headers):
        """Test getting daily activity statistics."""
        # Create jobs over the past week
        today = datetime.utcnow().date()

        for i in range(7):
            date = today - timedelta(days=i)
            # Create 2-5 jobs per day
            jobs_count = 5 - i % 3
            for j in range(jobs_count):
                job = JobFactory(user=sample_user)
                job.created_at = datetime.combine(date, datetime.min.time())
                db_session.add(job)

        db_session.commit()

        with patch("src.api.routers.analytics.get_current_user", return_value=sample_user):
            response = client.get(
                "/api/v1/analytics/activity/daily?days=7",
                headers=auth_headers
            )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 7
        assert all("date" in item for item in data)
        assert all("jobs_created" in item for item in data)
        assert all(item["jobs_created"] > 0 for item in data)

    def test_get_industry_distribution(self, client, db_session, sample_user, auth_headers):
        """Test getting industry distribution of enriched companies."""
        job = JobFactory(user=sample_user)

        # Create enriched records with different industries
        industries = [
            "Technology", "Technology", "Technology", "Technology",  # 40%
            "Healthcare", "Healthcare", "Healthcare",  # 30%
            "Finance", "Finance",  # 20%
            "Retail"  # 10%
        ]

        for industry in industries:
            record = RecordFactory(job=job)
            record.status = "enriched"
            record.enriched_data = {"industry": industry}
            db_session.add(record)

        db_session.commit()

        with patch("src.api.routers.analytics.get_current_user", return_value=sample_user):
            response = client.get(
                "/api/v1/analytics/industries/distribution",
                headers=auth_headers
            )

        assert response.status_code == 200
        data = response.json()

        # Check industry distribution
        industry_map = {item["industry"]: item["count"] for item in data}
        assert industry_map["Technology"] == 4
        assert industry_map["Healthcare"] == 3
        assert industry_map["Finance"] == 2
        assert industry_map["Retail"] == 1

    def test_get_performance_metrics(self, client, db_session, sample_user, auth_headers):
        """Test getting performance metrics."""
        # Create completed jobs with timing data
        jobs = []
        for i in range(5):
            job = JobFactory(
                user=sample_user,
                status="completed",
                total_records=100
            )
            job.started_at = datetime.utcnow() - timedelta(hours=2)
            job.completed_at = datetime.utcnow() - timedelta(hours=1)
            job.successful_records = 90 + i
            job.failed_records = 10 - i
            jobs.append(job)

        db_session.add_all(jobs)
        db_session.commit()

        with patch("src.api.routers.analytics.get_current_user", return_value=sample_user):
            response = client.get(
                "/api/v1/analytics/performance/metrics",
                headers=auth_headers
            )

        assert response.status_code == 200
        data = response.json()
        assert "average_processing_time" in data
        assert "average_success_rate" in data
        assert "total_processing_hours" in data
        assert data["average_processing_time"] == 60.0  # 1 hour in minutes
        assert data["average_success_rate"] > 90.0

    def test_get_top_companies(self, client, db_session, sample_user, auth_headers):
        """Test getting top enriched companies by size."""
        job = JobFactory(user=sample_user)

        # Create enriched records with company data
        companies_data = [
            {"name": "Big Corp", "size": "500+", "employee_count": 5000},
            {"name": "Medium Inc", "size": "201-500", "employee_count": 300},
            {"name": "Small LLC", "size": "11-50", "employee_count": 25},
            {"name": "Huge Enterprise", "size": "500+", "employee_count": 10000},
            {"name": "Startup", "size": "1-10", "employee_count": 5}
        ]

        for company_data in companies_data:
            record = RecordFactory(job=job, company_name=company_data["name"])
            record.status = "enriched"
            record.enriched_data = company_data
            db_session.add(record)

        db_session.commit()

        with patch("src.api.routers.analytics.get_current_user", return_value=sample_user):
            response = client.get(
                "/api/v1/analytics/companies/top?limit=3",
                headers=auth_headers
            )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3
        assert data[0]["name"] == "Huge Enterprise"
        assert data[1]["name"] == "Big Corp"
        assert data[2]["name"] == "Medium Inc"

    def test_get_enrichment_timeline(self, client, db_session, sample_user, auth_headers):
        """Test getting enrichment timeline."""
        job = JobFactory(user=sample_user)

        # Create records enriched at different times
        now = datetime.utcnow()
        for i in range(24):  # Last 24 hours
            record = RecordFactory(job=job)
            record.status = "enriched"
            record.processed_at = now - timedelta(hours=i)
            db_session.add(record)

        db_session.commit()

        with patch("src.api.routers.analytics.get_current_user", return_value=sample_user):
            response = client.get(
                "/api/v1/analytics/enrichment/timeline?hours=24",
                headers=auth_headers
            )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 24
        assert all("hour" in item for item in data)
        assert all("count" in item for item in data)
        assert sum(item["count"] for item in data) == 24

    def test_export_analytics_report(self, client, db_session, sample_user, auth_headers):
        """Test exporting analytics report."""
        # Create some data
        jobs = [JobFactory(user=sample_user, status="completed") for _ in range(5)]
        db_session.add_all(jobs)
        db_session.commit()

        with patch("src.api.routers.analytics.get_current_user", return_value=sample_user):
            response = client.get(
                "/api/v1/analytics/export/report?format=json",
                headers=auth_headers
            )

        assert response.status_code == 200
        data = response.json()
        assert "generated_at" in data
        assert "user_statistics" in data
        assert "job_statistics" in data
        assert "enrichment_statistics" in data

    def test_analytics_date_filtering(self, client, db_session, sample_user, auth_headers):
        """Test analytics with date range filtering."""
        # Create jobs in different date ranges
        old_job = JobFactory(user=sample_user)
        old_job.created_at = datetime.utcnow() - timedelta(days=60)

        recent_job = JobFactory(user=sample_user)
        recent_job.created_at = datetime.utcnow() - timedelta(days=5)

        db_session.add_all([old_job, recent_job])
        db_session.commit()

        with patch("src.api.routers.analytics.get_current_user", return_value=sample_user):
            # Get analytics for last 30 days
            response = client.get(
                "/api/v1/analytics/jobs/statistics?days=30",
                headers=auth_headers
            )

        assert response.status_code == 200
        data = response.json()
        assert data["total_jobs"] == 1  # Only recent job
