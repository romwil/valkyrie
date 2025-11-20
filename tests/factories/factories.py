"""Test factories for generating test data."""

import factory
from factory.alchemy import SQLAlchemyModelFactory
from faker import Faker
from datetime import datetime, timedelta
import random

from src.models import User, Company, Record, Job
from tests.conftest import TestingSessionLocal

fake = Faker()


class BaseFactory(SQLAlchemyModelFactory):
    """Base factory with session configuration."""
    class Meta:
        abstract = True
        sqlalchemy_session = TestingSessionLocal()
        sqlalchemy_session_persistence = "commit"


class UserFactory(BaseFactory):
    """Factory for creating test users."""
    class Meta:
        model = User

    email = factory.LazyAttribute(lambda _: fake.unique.email())
    username = factory.LazyAttribute(lambda _: fake.unique.user_name())
    full_name = factory.LazyAttribute(lambda _: fake.name())
    hashed_password = "$2b$12$test_hashed_password"
    is_active = True
    is_superuser = False
    created_at = factory.LazyFunction(datetime.utcnow)
    updated_at = factory.LazyFunction(datetime.utcnow)


class CompanyFactory(BaseFactory):
    """Factory for creating test companies."""
    class Meta:
        model = Company

    name = factory.LazyAttribute(lambda _: fake.company())
    domain = factory.LazyAttribute(lambda obj: obj.name.lower().replace(" ", "") + ".com")
    industry = factory.LazyAttribute(
        lambda _: random.choice(["Technology", "Healthcare", "Finance", "Retail", "Manufacturing"])
    )
    size = factory.LazyAttribute(
        lambda _: random.choice(["1-10", "11-50", "51-200", "201-500", "500+"])
    )
    revenue = factory.LazyAttribute(
        lambda _: random.choice(["<$1M", "$1M-$10M", "$10M-$50M", "$50M-$100M", "$100M+"])
    )
    description = factory.LazyAttribute(lambda _: fake.text(max_nb_chars=200))
    founded_year = factory.LazyAttribute(lambda _: random.randint(1990, 2023))
    headquarters = factory.LazyAttribute(lambda _: fake.city() + ", " + fake.country())
    employee_count = factory.LazyAttribute(lambda _: random.randint(10, 5000))
    linkedin_url = factory.LazyAttribute(
        lambda obj: f"https://linkedin.com/company/{obj.name.lower().replace(' ', '-')}"
    )
    website = factory.LazyAttribute(lambda obj: f"https://{obj.domain}")
    phone = factory.LazyAttribute(lambda _: fake.phone_number())
    address = factory.LazyAttribute(lambda _: fake.address())
    created_at = factory.LazyFunction(datetime.utcnow)
    updated_at = factory.LazyFunction(datetime.utcnow)


class JobFactory(BaseFactory):
    """Factory for creating test jobs."""
    class Meta:
        model = Job

    name = factory.LazyAttribute(lambda _: f"Enrichment Job - {fake.catch_phrase()}")
    user = factory.SubFactory(UserFactory)
    status = "pending"
    total_records = factory.LazyAttribute(lambda _: random.randint(10, 1000))
    processed_records = 0
    successful_records = 0
    failed_records = 0
    error_message = None
    started_at = None
    completed_at = None
    created_at = factory.LazyFunction(datetime.utcnow)
    updated_at = factory.LazyFunction(datetime.utcnow)

    @factory.post_generation
    def set_processing_status(obj, create, extracted, **kwargs):
        """Optionally set job to processing status with some progress."""
        if extracted == "processing":
            obj.status = "processing"
            obj.started_at = datetime.utcnow()
            obj.processed_records = int(obj.total_records * 0.3)
            obj.successful_records = int(obj.processed_records * 0.9)
            obj.failed_records = obj.processed_records - obj.successful_records

    @factory.post_generation
    def set_completed_status(obj, create, extracted, **kwargs):
        """Optionally set job to completed status."""
        if extracted == "completed":
            obj.status = "completed"
            obj.started_at = datetime.utcnow() - timedelta(minutes=30)
            obj.completed_at = datetime.utcnow()
            obj.processed_records = obj.total_records
            obj.successful_records = int(obj.total_records * 0.95)
            obj.failed_records = obj.total_records - obj.successful_records


class RecordFactory(BaseFactory):
    """Factory for creating test records."""
    class Meta:
        model = Record

    job = factory.SubFactory(JobFactory)
    company_name = factory.LazyAttribute(lambda _: fake.company())
    email = factory.LazyAttribute(lambda _: fake.email())
    phone = factory.LazyAttribute(lambda _: fake.phone_number())
    website = factory.LazyAttribute(
        lambda obj: f"https://{obj.company_name.lower().replace(' ', '')}.com"
    )
    address = factory.LazyAttribute(lambda _: fake.address())
    status = "pending"
    enriched_data = None
    error_message = None
    processed_at = None
    created_at = factory.LazyFunction(datetime.utcnow)
    updated_at = factory.LazyFunction(datetime.utcnow)

    @factory.post_generation
    def set_enriched_status(obj, create, extracted, **kwargs):
        """Optionally set record to enriched status with data."""
        if extracted == "enriched":
            obj.status = "enriched"
            obj.processed_at = datetime.utcnow()
            obj.enriched_data = {
                "industry": random.choice(["Technology", "Healthcare", "Finance"]),
                "size": random.choice(["1-10", "11-50", "51-200"]),
                "revenue": random.choice(["<$1M", "$1M-$10M", "$10M-$50M"]),
                "description": fake.text(max_nb_chars=200),
                "key_products": [fake.word() for _ in range(3)],
                "target_market": random.choice(["B2B", "B2C", "Enterprise"]),
                "competitors": [fake.company() for _ in range(2)],
                "recent_news": fake.sentence()
            }

    @factory.post_generation
    def set_failed_status(obj, create, extracted, **kwargs):
        """Optionally set record to failed status."""
        if extracted == "failed":
            obj.status = "failed"
            obj.processed_at = datetime.utcnow()
            obj.error_message = "Failed to enrich: " + fake.sentence()


# Batch creation helpers
def create_job_with_records(user=None, num_records=10, job_status="pending", record_distribution=None):
    """Create a job with associated records.

    Args:
        user: User instance (creates one if not provided)
        num_records: Number of records to create
        job_status: Status of the job
        record_distribution: Dict with keys 'pending', 'enriched', 'failed' and values as percentages

    Returns:
        Tuple of (job, records)
    """
    if user is None:
        user = UserFactory()

    job = JobFactory(user=user, total_records=num_records)

    if record_distribution is None:
        record_distribution = {"pending": 1.0, "enriched": 0.0, "failed": 0.0}

    records = []
    for i in range(num_records):
        rand = random.random()
        if rand < record_distribution.get("enriched", 0):
            record = RecordFactory(job=job, set_enriched_status="enriched")
        elif rand < (record_distribution.get("enriched", 0) + record_distribution.get("failed", 0)):
            record = RecordFactory(job=job, set_failed_status="failed")
        else:
            record = RecordFactory(job=job)
        records.append(record)

    # Update job status based on records
    if job_status == "processing":
        job.set_processing_status = "processing"
    elif job_status == "completed":
        job.set_completed_status = "completed"

    return job, records
