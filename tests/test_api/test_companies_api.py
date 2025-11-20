"""Unit tests for Companies API endpoints."""

import pytest
from unittest.mock import patch

from src.models import Company
from tests.factories import CompanyFactory


class TestCompaniesAPI:
    """Test companies API endpoints."""

    def test_create_company(self, client, auth_headers):
        """Test creating a new company."""
        company_data = {
            "name": "New Tech Corp",
            "domain": "newtechcorp.com",
            "industry": "Technology",
            "size": "100-500",
            "revenue": "$10M-$50M",
            "description": "An innovative technology company"
        }

        response = client.post("/api/v1/companies/", json=company_data, headers=auth_headers)

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "New Tech Corp"
        assert data["domain"] == "newtechcorp.com"

    def test_list_companies(self, client, db_session, auth_headers):
        """Test listing companies."""
        companies = [CompanyFactory() for _ in range(20)]
        db_session.add_all(companies)
        db_session.commit()

        response = client.get("/api/v1/companies/", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 20

    def test_search_companies(self, client, db_session, auth_headers):
        """Test searching companies by name."""
        # Create companies with specific names
        tech_companies = [
            CompanyFactory(name="Tech Solutions Inc"),
            CompanyFactory(name="Advanced Tech Corp"),
            CompanyFactory(name="TechnoLogic Systems")
        ]
        other_companies = [
            CompanyFactory(name="Finance Group LLC"),
            CompanyFactory(name="Healthcare Partners")
        ]

        db_session.add_all(tech_companies + other_companies)
        db_session.commit()

        response = client.get("/api/v1/companies/?search=tech", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 3
        assert all("tech" in company["name"].lower() for company in data)

    def test_get_company_by_domain(self, client, db_session, auth_headers):
        """Test getting company by domain."""
        company = CompanyFactory(domain="uniquedomain.com")
        db_session.add(company)
        db_session.commit()

        response = client.get("/api/v1/companies/by-domain/uniquedomain.com", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["domain"] == "uniquedomain.com"
        assert data["id"] == company.id

    def test_update_company(self, client, db_session, sample_company, auth_headers):
        """Test updating company information."""
        update_data = {
            "industry": "Software",
            "size": "500+",
            "revenue": "$100M+",
            "description": "Updated description"
        }

        response = client.patch(
            f"/api/v1/companies/{sample_company.id}",
            json=update_data,
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["industry"] == "Software"
        assert data["size"] == "500+"
        assert data["description"] == "Updated description"

    def test_delete_company(self, client, db_session, sample_company, auth_headers):
        """Test deleting a company."""
        response = client.delete(f"/api/v1/companies/{sample_company.id}", headers=auth_headers)

        assert response.status_code == 204
        assert db_session.query(Company).filter_by(id=sample_company.id).first() is None

    def test_filter_companies_by_industry(self, client, db_session, auth_headers):
        """Test filtering companies by industry."""
        # Create companies with different industries
        tech_companies = [CompanyFactory(industry="Technology") for _ in range(5)]
        healthcare_companies = [CompanyFactory(industry="Healthcare") for _ in range(3)]
        finance_companies = [CompanyFactory(industry="Finance") for _ in range(2)]

        db_session.add_all(tech_companies + healthcare_companies + finance_companies)
        db_session.commit()

        # Filter by Technology
        response = client.get("/api/v1/companies/?industry=Technology", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 5
        assert all(company["industry"] == "Technology" for company in data)

        # Filter by Healthcare
        response = client.get("/api/v1/companies/?industry=Healthcare", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 3
        assert all(company["industry"] == "Healthcare" for company in data)

    def test_filter_companies_by_size(self, client, db_session, auth_headers):
        """Test filtering companies by size."""
        # Create companies with different sizes
        small_companies = [CompanyFactory(size="1-10") for _ in range(4)]
        medium_companies = [CompanyFactory(size="11-50") for _ in range(3)]
        large_companies = [CompanyFactory(size="500+") for _ in range(2)]

        db_session.add_all(small_companies + medium_companies + large_companies)
        db_session.commit()

        # Filter by small size
        response = client.get("/api/v1/companies/?size=1-10", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 4
        assert all(company["size"] == "1-10" for company in data)

    def test_company_pagination(self, client, db_session, auth_headers):
        """Test company listing pagination."""
        # Create many companies
        companies = [CompanyFactory() for _ in range(30)]
        db_session.add_all(companies)
        db_session.commit()

        # First page
        response = client.get("/api/v1/companies/?skip=0&limit=10", headers=auth_headers)
        assert response.status_code == 200
        assert len(response.json()) == 10

        # Second page
        response = client.get("/api/v1/companies/?skip=10&limit=10", headers=auth_headers)
        assert response.status_code == 200
        assert len(response.json()) == 10

        # Third page
        response = client.get("/api/v1/companies/?skip=20&limit=10", headers=auth_headers)
        assert response.status_code == 200
        assert len(response.json()) == 10

    def test_company_sorting(self, client, db_session, auth_headers):
        """Test sorting companies by different fields."""
        # Create companies with specific names for sorting
        companies = [
            CompanyFactory(name="Alpha Corp"),
            CompanyFactory(name="Beta Inc"),
            CompanyFactory(name="Gamma LLC"),
            CompanyFactory(name="Delta Systems")
        ]
        db_session.add_all(companies)
        db_session.commit()

        # Sort by name ascending
        response = client.get("/api/v1/companies/?sort_by=name&order=asc", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        names = [c["name"] for c in data[:4]]
        assert names[0] == "Alpha Corp"
        assert names[-1] == "Delta Systems"

        # Sort by name descending
        response = client.get("/api/v1/companies/?sort_by=name&order=desc", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        names = [c["name"] for c in data[:4]]
        assert names[0] == "Gamma LLC"
        assert names[-1] == "Alpha Corp"

    def test_company_duplicate_domain(self, client, db_session, auth_headers):
        """Test that duplicate domains are not allowed."""
        # Create a company
        company = CompanyFactory(domain="existing.com")
        db_session.add(company)
        db_session.commit()

        # Try to create another company with the same domain
        company_data = {
            "name": "Another Company",
            "domain": "existing.com",
            "industry": "Technology"
        }

        response = client.post("/api/v1/companies/", json=company_data, headers=auth_headers)
        assert response.status_code == 400
        assert "already exists" in response.json()["detail"].lower()
