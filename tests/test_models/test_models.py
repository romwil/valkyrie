"""Unit tests for database models."""

import pytest
from datetime import datetime, timedelta
from sqlalchemy.exc import IntegrityError

from src.models import User, Company, Record, Job
from tests.factories import UserFactory, CompanyFactory, JobFactory, RecordFactory


class TestUserModel:
    """Test User model functionality."""

    def test_create_user(self, db_session):
        """Test creating a new user."""
        user = User(
            email="test@example.com",
            username="testuser",
            full_name="Test User",
            hashed_password="hashed_password_here"
        )
        db_session.add(user)
        db_session.commit()

        assert user.id is not None
        assert user.email == "test@example.com"
        assert user.is_active is True
        assert user.is_superuser is False
        assert user.created_at is not None

    def test_user_unique_email(self, db_session):
        """Test that email must be unique."""
        user1 = UserFactory(email="unique@example.com")
        db_session.add(user1)
        db_session.commit()

        user2 = User(
            email="unique@example.com",
            username="different",
            full_name="Different User",
            hashed_password="password"
        )
        db_session.add(user2)

        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_user_relationships(self, db_session):
        """Test user relationships with jobs."""
        user = UserFactory()
        jobs = [JobFactory(user=user) for _ in range(3)]
        db_session.add_all([user] + jobs)
        db_session.commit()

        assert len(user.jobs) == 3
        assert all(job.user_id == user.id for job in user.jobs)

    def test_user_factory(self, db_session):
        """Test UserFactory creates valid users."""
        users = [UserFactory() for _ in range(5)]
        db_session.add_all(users)
        db_session.commit()

        assert len(users) == 5
        assert all(user.id is not None for user in users)
        assert len(set(user.email for user in users)) == 5  # All unique


class TestCompanyModel:
    """Test Company model functionality."""

    def test_create_company(self, db_session):
        """Test creating a new company."""
        company = Company(
            name="Test Corp",
            domain="testcorp.com",
            industry="Technology",
            size="100-500",
            revenue="$10M-$50M"
        )
        db_session.add(company)
        db_session.commit()

        assert company.id is not None
        assert company.name == "Test Corp"
        assert company.created_at is not None

    def test_company_optional_fields(self, db_session):
        """Test company with all optional fields."""
        company = CompanyFactory(
            description="A leading tech company",
            founded_year=2010,
            headquarters="San Francisco, CA",
            employee_count=250,
            linkedin_url="https://linkedin.com/company/testcorp",
            website="https://testcorp.com",
            phone="+1-555-0123",
            address="123 Tech Street, SF, CA 94105"
        )
        db_session.add(company)
        db_session.commit()

        assert company.founded_year == 2010
        assert company.employee_count == 250
        assert "San Francisco" in company.headquarters

    def test_company_factory(self, db_session):
        """Test CompanyFactory creates valid companies."""
        companies = [CompanyFactory() for _ in range(10)]
        db_session.add_all(companies)
        db_session.commit()

        assert len(companies) == 10
        assert all(company.id is not None for company in companies)
        assert all(company.domain.endswith(".com") for company in companies)


class TestJobModel:
    """Test Job model functionality."""

    def test_create_job(self, db_session, sample_user):
        """Test creating a new job."""
        job = Job(
            name="Data Enrichment Job",
            user_id=sample_user.id,
            total_records=100
        )
        db_session.add(job)
        db_session.commit()

        assert job.id is not None
        assert job.status == "pending"
        assert job.processed_records == 0
        assert job.successful_records == 0
        assert job.failed_records == 0

    def test_job_status_transitions(self, db_session, sample_user):
        """Test job status transitions."""
        job = JobFactory(user=sample_user)
        db_session.add(job)
        db_session.commit()

        # Start processing
        job.status = "processing"
        job.started_at = datetime.utcnow()
        db_session.commit()

        assert job.status == "processing"
        assert job.started_at is not None

        # Complete job
        job.status = "completed"
        job.completed_at = datetime.utcnow()
        job.processed_records = job.total_records
        job.successful_records = 95
        job.failed_records = 5
        db_session.commit()

        assert job.status == "completed"
        assert job.completed_at > job.started_at

    def test_job_with_error(self, db_session, sample_user):
        """Test job with error status."""
        job = JobFactory(
            user=sample_user,
            status="failed",
            error_message="API rate limit exceeded"
        )
        db_session.add(job)
        db_session.commit()

        assert job.status == "failed"
        assert "rate limit" in job.error_message

    def test_job_relationships(self, db_session, sample_user):
        """Test job relationships with records."""
        job = JobFactory(user=sample_user, total_records=5)
        records = [RecordFactory(job=job) for _ in range(5)]
        db_session.add_all([job] + records)
        db_session.commit()

        assert len(job.records) == 5
        assert all(record.job_id == job.id for record in job.records)


class TestRecordModel:
    """Test Record model functionality."""

    def test_create_record(self, db_session, sample_job):
        """Test creating a new record."""
        record = Record(
            job_id=sample_job.id,
            company_name="Test Company",
            email="contact@testcompany.com",
            phone="+1-555-0123",
            website="https://testcompany.com"
        )
        db_session.add(record)
        db_session.commit()

        assert record.id is not None
        assert record.status == "pending"
        assert record.enriched_data is None

    def test_record_enrichment(self, db_session, sample_job):
        """Test record enrichment process."""
        record = RecordFactory(job=sample_job)
        db_session.add(record)
        db_session.commit()

        # Enrich record
        enriched_data = {
            "industry": "Technology",
            "size": "50-200",
            "revenue": "$5M-$10M",
            "description": "A software development company",
            "key_products": ["SaaS Platform", "Mobile Apps"],
            "competitors": ["Competitor A", "Competitor B"]
        }

        record.status = "enriched"
        record.enriched_data = enriched_data
        record.processed_at = datetime.utcnow()
        db_session.commit()

        assert record.status == "enriched"
        assert record.enriched_data["industry"] == "Technology"
        assert len(record.enriched_data["key_products"]) == 2
        assert record.processed_at is not None

    def test_record_failure(self, db_session, sample_job):
        """Test record enrichment failure."""
        record = RecordFactory(
            job=sample_job,
            set_failed_status="failed"
        )
        db_session.add(record)
        db_session.commit()

        assert record.status == "failed"
        assert record.error_message is not None
        assert record.processed_at is not None

    def test_record_factory_variations(self, db_session, sample_job):
        """Test RecordFactory with different statuses."""
        pending_record = RecordFactory(job=sample_job)
        enriched_record = RecordFactory(job=sample_job, set_enriched_status="enriched")
        failed_record = RecordFactory(job=sample_job, set_failed_status="failed")

        db_session.add_all([pending_record, enriched_record, failed_record])
        db_session.commit()

        assert pending_record.status == "pending"
        assert enriched_record.status == "enriched"
        assert enriched_record.enriched_data is not None
        assert failed_record.status == "failed"
        assert failed_record.error_message is not None


class TestModelRelationships:
    """Test relationships between models."""

    def test_cascade_delete_user_jobs(self, db_session):
        """Test that deleting a user cascades to jobs."""
        user = UserFactory()
        jobs = [JobFactory(user=user) for _ in range(3)]
        db_session.add_all([user] + jobs)
        db_session.commit()

        user_id = user.id
        job_ids = [job.id for job in jobs]

        db_session.delete(user)
        db_session.commit()

        # Check that user and jobs are deleted
        assert db_session.query(User).filter_by(id=user_id).first() is None
        for job_id in job_ids:
            assert db_session.query(Job).filter_by(id=job_id).first() is None

    def test_cascade_delete_job_records(self, db_session, sample_user):
        """Test that deleting a job cascades to records."""
        job = JobFactory(user=sample_user)
        records = [RecordFactory(job=job) for _ in range(5)]
        db_session.add_all([job] + records)
        db_session.commit()

        job_id = job.id
        record_ids = [record.id for record in records]

        db_session.delete(job)
        db_session.commit()

        # Check that job and records are deleted
        assert db_session.query(Job).filter_by(id=job_id).first() is None
        for record_id in record_ids:
            assert db_session.query(Record).filter_by(id=record_id).first() is None

    def test_job_statistics(self, db_session, sample_user):
        """Test job statistics calculation."""
        job = JobFactory(user=sample_user, total_records=10)

        # Create records with different statuses
        for i in range(6):
            RecordFactory(job=job, set_enriched_status="enriched")
        for i in range(2):
            RecordFactory(job=job, set_failed_status="failed")
        for i in range(2):
            RecordFactory(job=job)  # pending

        db_session.add(job)
        db_session.commit()

        # Calculate statistics
        enriched_count = sum(1 for r in job.records if r.status == "enriched")
        failed_count = sum(1 for r in job.records if r.status == "failed")
        pending_count = sum(1 for r in job.records if r.status == "pending")

        assert enriched_count == 6
        assert failed_count == 2
        assert pending_count == 2
        assert len(job.records) == 10
