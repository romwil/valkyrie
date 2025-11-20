-- Project Valkyrie Database Schema
-- PostgreSQL schema for LLM-driven data action platform
-- Created: 2024-11-19

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm"; -- For text search optimization

-- Drop existing tables if they exist (for clean setup)
DROP TABLE IF EXISTS audit_log CASCADE;
DROP TABLE IF EXISTS records CASCADE;
DROP TABLE IF EXISTS companies CASCADE;
DROP TABLE IF EXISTS jobs CASCADE;

-- Create custom types
DO $$ BEGIN
    CREATE TYPE job_status AS ENUM (
        'pending',
        'processing',
        'completed',
        'failed',
        'cancelled'
    );
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE record_status AS ENUM (
        'pending',
        'processing',
        'enriched',
        'failed',
        'skipped'
    );
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Jobs table: Tracks enrichment job batches
CREATE TABLE jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    status job_status NOT NULL DEFAULT 'pending',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    input_file VARCHAR(500) NOT NULL,
    output_file VARCHAR(500),
    total_records INTEGER NOT NULL DEFAULT 0,
    processed_records INTEGER NOT NULL DEFAULT 0,
    error_count INTEGER NOT NULL DEFAULT 0,
    configuration JSONB DEFAULT '{}',
    metadata JSONB DEFAULT '{}',
    error_details JSONB DEFAULT '[]',

    -- Constraints
    CONSTRAINT chk_processed_records CHECK (processed_records <= total_records),
    CONSTRAINT chk_error_count CHECK (error_count >= 0),
    CONSTRAINT chk_dates CHECK (started_at IS NULL OR started_at >= created_at),
    CONSTRAINT chk_completion CHECK (
        (completed_at IS NULL) OR 
        (started_at IS NOT NULL AND completed_at >= started_at)
    )
);

-- Companies table: Master data management for companies
CREATE TABLE companies (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    domain VARCHAR(255),
    mdm_flag BOOLEAN NOT NULL DEFAULT false,
    metadata JSONB DEFAULT '{}',
    enrichment_data JSONB DEFAULT '{}',
    industry VARCHAR(100),
    employee_count INTEGER,
    revenue_range VARCHAR(50),
    headquarters_location VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_enriched_at TIMESTAMP WITH TIME ZONE,

    -- Constraints
    CONSTRAINT chk_employee_count CHECK (employee_count IS NULL OR employee_count >= 0),
    CONSTRAINT uq_domain UNIQUE(domain)
);

-- Records table: Individual records for processing
CREATE TABLE records (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    job_id UUID NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    company_id UUID REFERENCES companies(id) ON DELETE SET NULL,
    original_data JSONB NOT NULL,
    enriched_data JSONB DEFAULT '{}',
    llm_response JSONB DEFAULT '{}',
    status record_status NOT NULL DEFAULT 'pending',
    processed_at TIMESTAMP WITH TIME ZONE,
    processing_time_ms INTEGER,
    retry_count INTEGER NOT NULL DEFAULT 0,
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,

    -- Constraints
    CONSTRAINT chk_retry_count CHECK (retry_count >= 0),
    CONSTRAINT chk_processing_time CHECK (processing_time_ms IS NULL OR processing_time_ms >= 0)
);

-- Audit log table: Tracks all system actions
CREATE TABLE audit_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    job_id UUID REFERENCES jobs(id) ON DELETE CASCADE,
    record_id UUID REFERENCES records(id) ON DELETE CASCADE,
    action VARCHAR(100) NOT NULL,
    details JSONB DEFAULT '{}',
    user_id VARCHAR(255),
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,

    -- Constraints
    CONSTRAINT chk_action_not_empty CHECK (action != '')
);

-- Create indexes for performance optimization

-- Jobs table indexes
CREATE INDEX idx_jobs_status ON jobs(status) WHERE status IN ('pending', 'processing');
CREATE INDEX idx_jobs_created_at ON jobs(created_at DESC);
CREATE INDEX idx_jobs_updated_at ON jobs(updated_at DESC);
CREATE INDEX idx_jobs_input_file ON jobs(input_file);

-- Companies table indexes
CREATE INDEX idx_companies_name_trgm ON companies USING gin(name gin_trgm_ops);
CREATE INDEX idx_companies_domain ON companies(domain) WHERE domain IS NOT NULL;
CREATE INDEX idx_companies_mdm_flag ON companies(mdm_flag) WHERE mdm_flag = true;
CREATE INDEX idx_companies_metadata ON companies USING gin(metadata);
CREATE INDEX idx_companies_industry ON companies(industry) WHERE industry IS NOT NULL;
CREATE INDEX idx_companies_updated_at ON companies(updated_at DESC);

-- Records table indexes
CREATE INDEX idx_records_job_id ON records(job_id);
CREATE INDEX idx_records_company_id ON records(company_id) WHERE company_id IS NOT NULL;
CREATE INDEX idx_records_status ON records(status) WHERE status IN ('pending', 'processing');
CREATE INDEX idx_records_job_status ON records(job_id, status);
CREATE INDEX idx_records_processed_at ON records(processed_at DESC) WHERE processed_at IS NOT NULL;
CREATE INDEX idx_records_original_data ON records USING gin(original_data);
CREATE INDEX idx_records_enriched_data ON records USING gin(enriched_data);
CREATE INDEX idx_records_retry_count ON records(retry_count) WHERE retry_count > 0;

-- Audit log indexes
CREATE INDEX idx_audit_log_job_id ON audit_log(job_id) WHERE job_id IS NOT NULL;
CREATE INDEX idx_audit_log_record_id ON audit_log(record_id) WHERE record_id IS NOT NULL;
CREATE INDEX idx_audit_log_action ON audit_log(action);
CREATE INDEX idx_audit_log_created_at ON audit_log(created_at DESC);
CREATE INDEX idx_audit_log_user_id ON audit_log(user_id) WHERE user_id IS NOT NULL;

-- Create update timestamp trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply update timestamp triggers
CREATE TRIGGER update_jobs_updated_at BEFORE UPDATE ON jobs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_companies_updated_at BEFORE UPDATE ON companies
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_records_updated_at BEFORE UPDATE ON records
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Create audit trigger function
CREATE OR REPLACE FUNCTION audit_trigger_function()
RETURNS TRIGGER AS $$
DECLARE
    audit_action TEXT;
    job_id_val UUID;
    record_id_val UUID;
BEGIN
    -- Determine the action
    IF TG_OP = 'INSERT' THEN
        audit_action := TG_TABLE_NAME || '_created';
    ELSIF TG_OP = 'UPDATE' THEN
        audit_action := TG_TABLE_NAME || '_updated';
    ELSIF TG_OP = 'DELETE' THEN
        audit_action := TG_TABLE_NAME || '_deleted';
    END IF;

    -- Extract job_id and record_id based on table
    IF TG_TABLE_NAME = 'jobs' THEN
        job_id_val := COALESCE(NEW.id, OLD.id);
        record_id_val := NULL;
    ELSIF TG_TABLE_NAME = 'records' THEN
        job_id_val := COALESCE(NEW.job_id, OLD.job_id);
        record_id_val := COALESCE(NEW.id, OLD.id);
    ELSIF TG_TABLE_NAME = 'companies' THEN
        job_id_val := NULL;
        record_id_val := NULL;
    END IF;

    -- Insert audit log entry
    INSERT INTO audit_log (job_id, record_id, action, details)
    VALUES (
        job_id_val,
        record_id_val,
        audit_action,
        jsonb_build_object(
            'table_name', TG_TABLE_NAME,
            'operation', TG_OP,
            'old_values', to_jsonb(OLD),
            'new_values', to_jsonb(NEW)
        )
    );

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply audit triggers to main tables
CREATE TRIGGER audit_jobs_trigger
    AFTER INSERT OR UPDATE OR DELETE ON jobs
    FOR EACH ROW EXECUTE FUNCTION audit_trigger_function();

CREATE TRIGGER audit_records_trigger
    AFTER INSERT OR UPDATE OR DELETE ON records
    FOR EACH ROW EXECUTE FUNCTION audit_trigger_function();

CREATE TRIGGER audit_companies_trigger
    AFTER INSERT OR UPDATE OR DELETE ON companies
    FOR EACH ROW EXECUTE FUNCTION audit_trigger_function();

-- Create views for common queries

-- Job summary view
CREATE OR REPLACE VIEW job_summary AS
SELECT 
    j.id,
    j.status,
    j.created_at,
    j.updated_at,
    j.started_at,
    j.completed_at,
    j.input_file,
    j.output_file,
    j.total_records,
    j.processed_records,
    j.error_count,
    ROUND(CASE 
        WHEN j.total_records > 0 
        THEN (j.processed_records::NUMERIC / j.total_records) * 100 
        ELSE 0 
    END, 2) AS completion_percentage,
    EXTRACT(EPOCH FROM (COALESCE(j.completed_at, CURRENT_TIMESTAMP) - j.started_at)) AS processing_time_seconds,
    COUNT(DISTINCT r.company_id) AS unique_companies_processed
FROM jobs j
LEFT JOIN records r ON j.id = r.job_id AND r.status = 'enriched'
GROUP BY j.id;

-- Company enrichment status view
CREATE OR REPLACE VIEW company_enrichment_status AS
SELECT 
    c.id,
    c.name,
    c.domain,
    c.mdm_flag,
    c.last_enriched_at,
    COUNT(DISTINCT r.id) AS total_records,
    COUNT(DISTINCT CASE WHEN r.status = 'enriched' THEN r.id END) AS enriched_records,
    MAX(r.processed_at) AS last_processed_at
FROM companies c
LEFT JOIN records r ON c.id = r.company_id
GROUP BY c.id;

-- Create functions for common operations

-- Function to get job statistics
CREATE OR REPLACE FUNCTION get_job_statistics(job_uuid UUID)
RETURNS TABLE (
    total_records INTEGER,
    processed_records INTEGER,
    pending_records INTEGER,
    failed_records INTEGER,
    success_rate NUMERIC,
    avg_processing_time_ms NUMERIC
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        COUNT(*)::INTEGER AS total_records,
        COUNT(CASE WHEN status = 'enriched' THEN 1 END)::INTEGER AS processed_records,
        COUNT(CASE WHEN status = 'pending' THEN 1 END)::INTEGER AS pending_records,
        COUNT(CASE WHEN status = 'failed' THEN 1 END)::INTEGER AS failed_records,
        ROUND(COUNT(CASE WHEN status = 'enriched' THEN 1 END)::NUMERIC / NULLIF(COUNT(*), 0) * 100, 2) AS success_rate,
        ROUND(AVG(processing_time_ms)::NUMERIC, 2) AS avg_processing_time_ms
    FROM records
    WHERE job_id = job_uuid;
END;
$$ LANGUAGE plpgsql;

-- Function to update job statistics
CREATE OR REPLACE FUNCTION update_job_statistics(job_uuid UUID)
RETURNS VOID AS $$
DECLARE
    stats RECORD;
BEGIN
    SELECT 
        COUNT(*) AS total,
        COUNT(CASE WHEN status IN ('enriched', 'skipped') THEN 1 END) AS processed,
        COUNT(CASE WHEN status = 'failed' THEN 1 END) AS errors
    INTO stats
    FROM records
    WHERE job_id = job_uuid;

    UPDATE jobs
    SET 
        total_records = stats.total,
        processed_records = stats.processed,
        error_count = stats.errors,
        status = CASE
            WHEN stats.processed = stats.total THEN 'completed'::job_status
            WHEN stats.errors > 0 AND stats.processed + stats.errors = stats.total THEN 'failed'::job_status
            ELSE status
        END
    WHERE id = job_uuid;
END;
$$ LANGUAGE plpgsql;

-- Function to find or create company
CREATE OR REPLACE FUNCTION find_or_create_company(
    p_name VARCHAR(255),
    p_domain VARCHAR(255) DEFAULT NULL
)
RETURNS UUID AS $$
DECLARE
    company_uuid UUID;
BEGIN
    -- First try to find by domain if provided
    IF p_domain IS NOT NULL THEN
        SELECT id INTO company_uuid
        FROM companies
        WHERE domain = p_domain
        LIMIT 1;

        IF company_uuid IS NOT NULL THEN
            RETURN company_uuid;
        END IF;
    END IF;

    -- Try to find by exact name match
    SELECT id INTO company_uuid
    FROM companies
    WHERE LOWER(name) = LOWER(p_name)
    LIMIT 1;

    IF company_uuid IS NOT NULL THEN
        RETURN company_uuid;
    END IF;

    -- Create new company
    INSERT INTO companies (name, domain)
    VALUES (p_name, p_domain)
    RETURNING id INTO company_uuid;

    RETURN company_uuid;
END;
$$ LANGUAGE plpgsql;

-- Function to clean up old audit logs
CREATE OR REPLACE FUNCTION cleanup_old_audit_logs(days_to_keep INTEGER DEFAULT 90)
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM audit_log
    WHERE created_at < CURRENT_TIMESTAMP - INTERVAL '1 day' * days_to_keep;

    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Create materialized view for performance reporting
CREATE MATERIALIZED VIEW IF NOT EXISTS job_performance_metrics AS
SELECT 
    DATE_TRUNC('hour', j.created_at) AS hour,
    COUNT(DISTINCT j.id) AS jobs_created,
    SUM(j.total_records) AS total_records_processed,
    AVG(EXTRACT(EPOCH FROM (j.completed_at - j.started_at))) AS avg_job_duration_seconds,
    SUM(j.error_count) AS total_errors,
    ROUND(AVG(CASE WHEN j.total_records > 0 THEN (j.processed_records::NUMERIC / j.total_records) * 100 ELSE 0 END), 2) AS avg_completion_rate
FROM jobs j
WHERE j.created_at >= CURRENT_TIMESTAMP - INTERVAL '30 days'
GROUP BY DATE_TRUNC('hour', j.created_at)
ORDER BY hour DESC;

-- Create index on materialized view
CREATE INDEX idx_job_performance_metrics_hour ON job_performance_metrics(hour DESC);

-- Grant permissions (adjust as needed for your environment)
-- GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO valkyrie_user;
-- GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO valkyrie_user;
-- GRANT ALL PRIVILEGES ON ALL FUNCTIONS IN SCHEMA public TO valkyrie_user;

-- Add comments for documentation
COMMENT ON TABLE jobs IS 'Tracks batch enrichment jobs with status and statistics';
COMMENT ON TABLE companies IS 'Master data management for company entities';
COMMENT ON TABLE records IS 'Individual records for processing within jobs';
COMMENT ON TABLE audit_log IS 'Comprehensive audit trail for all system actions';

COMMENT ON COLUMN jobs.mdm_flag IS 'Master Data Management flag indicating verified/golden record';
COMMENT ON COLUMN records.llm_response IS 'Raw response from LLM including metadata';
COMMENT ON COLUMN companies.enrichment_data IS 'Aggregated enrichment data from all sources';
