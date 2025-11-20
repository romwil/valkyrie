-- Sample data for Project Valkyrie
-- This file contains test data for development and testing

-- Enable UUID extension if not already enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Insert sample companies (Master Data)
INSERT INTO companies (id, name, domain, mdm_flag, industry, employee_count, revenue_range, headquarters_location, metadata, enrichment_data) VALUES
('550e8400-e29b-41d4-a716-446655440001', 'Acme Corporation', 'acme.com', true, 'Technology', 5000, '$100M-$500M', 'San Francisco, CA', 
 '{
    "founded_year": 2010,
    "public_company": true,
    "stock_symbol": "ACME",
    "linkedin_url": "https://linkedin.com/company/acme-corp"
  }'::jsonb,
 '{
    "technologies": ["AWS", "Python", "React"],
    "recent_news": "Launched new AI product line",
    "key_executives": [{"name": "John Smith", "title": "CEO"}, {"name": "Jane Doe", "title": "CTO"}],
    "competitors": ["TechCorp", "InnovateCo"],
    "last_funding_round": {"type": "Series C", "amount": "$50M", "date": "2023-06-15"}
  }'::jsonb),

('550e8400-e29b-41d4-a716-446655440002', 'Global Dynamics', 'globaldynamics.com', true, 'Manufacturing', 15000, '$1B+', 'Detroit, MI',
 '{
    "founded_year": 1985,
    "public_company": true,
    "stock_symbol": "GD",
    "fortune_500_rank": 287
  }'::jsonb,
 '{
    "subsidiaries": ["GD Automotive", "GD Aerospace"],
    "certifications": ["ISO 9001", "ISO 14001"],
    "major_clients": ["US Government", "Boeing", "Ford"],
    "sustainability_score": "A+"
  }'::jsonb),

('550e8400-e29b-41d4-a716-446655440003', 'StartupXYZ', 'startupxyz.io', false, 'SaaS', 50, '$1M-$10M', 'Austin, TX',
 '{
    "founded_year": 2021,
    "public_company": false,
    "funding_stage": "Series A"
  }'::jsonb,
 '{
    "product_focus": "B2B Sales Intelligence",
    "target_market": "Mid-market companies",
    "growth_rate": "300% YoY",
    "tech_stack": ["Node.js", "PostgreSQL", "Redis", "Kubernetes"]
  }'::jsonb),

('550e8400-e29b-41d4-a716-446655440004', 'Enterprise Solutions Inc', 'enterprise-solutions.com', true, 'Consulting', 8000, '$500M-$1B', 'New York, NY',
 '{
    "founded_year": 1999,
    "public_company": false,
    "specializations": ["Digital Transformation", "Cloud Migration", "AI/ML"]
  }'::jsonb,
 '{
    "partner_network": ["Microsoft", "AWS", "Google Cloud"],
    "industry_awards": ["Best Workplace 2023", "Innovation Leader 2023"],
    "global_offices": 25,
    "client_retention_rate": "95%"
  }'::jsonb);

-- Insert sample jobs
INSERT INTO jobs (id, name, description, job_type, status, configuration, created_by) VALUES
('660e8400-e29b-41d4-a716-446655440001', 'Tech Companies Enrichment Q4 2023', 
 'Enrich all technology companies in our database with latest funding and product information',
 'enrichment', 'completed',
 '{
    "target_industries": ["Technology", "SaaS"],
    "enrichment_fields": ["funding", "products", "key_personnel", "recent_news"],
    "data_sources": ["crunchbase", "linkedin", "news_apis"],
    "llm_model": "gpt-4",
    "batch_size": 100
  }'::jsonb,
 'user123'),

('660e8400-e29b-41d4-a716-446655440002', 'Manufacturing Sector Analysis', 
 'Analyze manufacturing companies for supply chain risks and opportunities',
 'analysis', 'running',
 '{
    "analysis_type": "supply_chain_risk",
    "regions": ["North America", "Europe"],
    "company_size": "enterprise",
    "risk_factors": ["geopolitical", "environmental", "financial"],
    "output_format": "detailed_report"
  }'::jsonb,
 'analyst456'),

('660e8400-e29b-41d4-a716-446655440003', 'Daily Lead Scoring Update', 
 'Update lead scores based on latest engagement and enrichment data',
 'scoring', 'pending',
 '{
    "scoring_model": "v2.5",
    "factors": {
        "engagement": 0.3,
        "fit": 0.4,
        "intent": 0.3
    },
    "threshold_settings": {
        "hot": 80,
        "warm": 60,
        "cold": 40
    },
    "schedule": "0 2 * * *"
  }'::jsonb,
 'system'),

('660e8400-e29b-41d4-a716-446655440004', 'Competitor Intelligence Gathering', 
 'Gather and analyze competitor activities and market positioning',
 'enrichment', 'failed',
 '{
    "competitors": ["CompetitorA", "CompetitorB", "CompetitorC"],
    "data_points": ["pricing", "features", "partnerships", "customer_wins"],
    "update_frequency": "weekly",
    "alert_threshold": "significant_changes"
  }'::jsonb,
 'marketing789');

-- Insert sample records
INSERT INTO records (id, job_id, company_id, source_data, enriched_data, processing_status, confidence_score, error_message) VALUES
('770e8400-e29b-41d4-a716-446655440001', '660e8400-e29b-41d4-a716-446655440001', '550e8400-e29b-41d4-a716-446655440001',
 '{
    "company_name": "Acme Corporation",
    "website": "acme.com",
    "last_contact": "2023-10-15",
    "sales_stage": "qualified"
  }'::jsonb,
 '{
    "latest_funding": {
        "round": "Series D",
        "amount": "$100M",
        "date": "2023-11-01",
        "investors": ["VentureCapital Partners", "Growth Equity Fund"]
    },
    "product_updates": [
        {"product": "AI Assistant Pro", "launch_date": "2023-10-20", "target_market": "Enterprise"},
        {"product": "Data Analytics Suite", "update": "v3.0", "features": ["Real-time processing", "ML integration"]}
    ],
    "key_personnel_changes": [
        {"position": "VP Sales", "name": "Sarah Johnson", "previous_company": "TechGiant Inc", "start_date": "2023-09-01"}
    ],
    "market_signals": {
        "hiring_velocity": "high",
        "expansion_indicators": ["New office in London", "100+ open positions"],
        "partnership_activity": "Strategic partnership with CloudProvider announced"
    }
  }'::jsonb,
 'completed', 0.95, NULL),

('770e8400-e29b-41d4-a716-446655440002', '660e8400-e29b-41d4-a716-446655440002', '550e8400-e29b-41d4-a716-446655440002',
 '{
    "company_name": "Global Dynamics",
    "industry": "Manufacturing",
    "analysis_scope": "supply_chain"
  }'::jsonb,
 '{
    "supply_chain_analysis": {
        "risk_score": 72,
        "identified_risks": [
            {"type": "geopolitical", "severity": "medium", "description": "25% of suppliers in high-risk regions"},
            {"type": "environmental", "severity": "low", "description": "Carbon footprint above industry average"}
        ],
        "opportunities": [
            {"area": "cost_reduction", "potential_savings": "$5M-$8M", "implementation": "Supplier consolidation"},
            {"area": "efficiency", "improvement": "15-20%", "method": "AI-driven demand forecasting"}
        ],
        "recommendations": [
            "Diversify supplier base in Southeast Asia",
            "Implement real-time supply chain visibility platform",
            "Establish strategic inventory buffers for critical components"
        ]
    }
  }'::jsonb,
 'completed', 0.88, NULL),

('770e8400-e29b-41d4-a716-446655440003', '660e8400-e29b-41d4-a716-446655440003', '550e8400-e29b-41d4-a716-446655440003',
 '{
    "company_name": "StartupXYZ",
    "current_score": 45,
    "last_engagement": "2023-11-10"
  }'::jsonb,
 NULL, 'pending', NULL, NULL),

('770e8400-e29b-41d4-a716-446655440004', '660e8400-e29b-41d4-a716-446655440004', '550e8400-e29b-41d4-a716-446655440001',
 '{
    "target_company": "Acme Corporation",
    "competitor_analysis": "requested"
  }'::jsonb,
 NULL, 'failed', NULL, 
 'API rate limit exceeded for competitor intelligence service. Retry after 2023-11-20 00:00:00');

-- Insert sample audit logs
INSERT INTO audit_logs (id, table_name, record_id, action, old_values, new_values, user_id, ip_address, user_agent) VALUES
('880e8400-e29b-41d4-a716-446655440001', 'jobs', '660e8400-e29b-41d4-a716-446655440001', 'INSERT',
 NULL,
 '{
    "id": "660e8400-e29b-41d4-a716-446655440001",
    "name": "Tech Companies Enrichment Q4 2023",
    "status": "pending",
    "created_by": "user123"
  }'::jsonb,
 'user123', '192.168.1.100', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'),

('880e8400-e29b-41d4-a716-446655440002', 'jobs', '660e8400-e29b-41d4-a716-446655440001', 'UPDATE',
 '{
    "status": "pending",
    "started_at": null
  }'::jsonb,
 '{
    "status": "running",
    "started_at": "2023-11-15T10:00:00Z"
  }'::jsonb,
 'system', '10.0.0.1', 'Valkyrie Job Processor v1.0'),

('880e8400-e29b-41d4-a716-446655440003', 'records', '770e8400-e29b-41d4-a716-446655440001', 'UPDATE',
 '{
    "processing_status": "pending",
    "enriched_data": null
  }'::jsonb,
 '{
    "processing_status": "completed",
    "enriched_data": {"latest_funding": {"round": "Series D", "amount": "$100M"}}
  }'::jsonb,
 'system', '10.0.0.2', 'Valkyrie Enrichment Engine v1.0'),

('880e8400-e29b-41d4-a716-446655440004', 'companies', '550e8400-e29b-41d4-a716-446655440001', 'UPDATE',
 '{
    "employee_count": 5000,
    "revenue_range": "$100M-$500M"
  }'::jsonb,
 '{
    "employee_count": 5500,
    "revenue_range": "$500M-$1B"
  }'::jsonb,
 'analyst456', '192.168.1.105', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)'),

('880e8400-e29b-41d4-a716-446655440005', 'jobs', '660e8400-e29b-41d4-a716-446655440001', 'UPDATE',
 '{
    "status": "running",
    "completed_at": null,
    "total_records": 0,
    "processed_records": 0
  }'::jsonb,
 '{
    "status": "completed",
    "completed_at": "2023-11-15T14:30:00Z",
    "total_records": 150,
    "processed_records": 150
  }'::jsonb,
 'system', '10.0.0.1', 'Valkyrie Job Processor v1.0');

-- Sample queries for testing and development

-- View all running jobs with their progress
/*
SELECT 
    j.name,
    j.status,
    j.created_at,
    j.started_at,
    COUNT(r.id) as total_records,
    COUNT(CASE WHEN r.processing_status = 'completed' THEN 1 END) as completed_records
FROM jobs j
LEFT JOIN records r ON j.id = r.job_id
WHERE j.status = 'running'
GROUP BY j.id, j.name, j.status, j.created_at, j.started_at;
*/

-- Find companies with recent enrichment data
/*
SELECT 
    c.name,
    c.domain,
    c.industry,
    r.enriched_data->>'latest_funding' as latest_funding,
    r.updated_at as last_enriched
FROM companies c
JOIN records r ON c.id = r.company_id
WHERE r.processing_status = 'completed'
    AND r.updated_at > NOW() - INTERVAL '7 days'
ORDER BY r.updated_at DESC;
*/

-- Audit trail for a specific company
/*
SELECT 
    al.created_at,
    al.action,
    al.table_name,
    al.user_id,
    al.old_values,
    al.new_values
FROM audit_logs al
WHERE al.record_id = '550e8400-e29b-41d4-a716-446655440001'
ORDER BY al.created_at DESC;
*/
