# Project Valkyrie Development Guide

## File Handling Best Practices

### Policy: Chunked File Writing for Large Files

When creating large files (especially SQL, JSON, or configuration files), always use a chunked writing approach to avoid string literal errors and memory issues.

#### Why This Policy?

We've observed that attempting to write large files in a single operation can lead to:
- Unterminated string literal errors
- Memory constraints
- Incomplete file writes
- Difficult-to-debug syntax errors

#### Implementation Pattern

```python
# GOOD: Chunked approach
# 1. Create file with header
with open('/path/to/file.sql', 'w') as f:
    f.write('-- File header
')
    f.write('-- Description

')

# 2. Write logical sections separately
section1 = '''-- Section 1
INSERT INTO table1 ...
'''
with open('/path/to/file.sql', 'a') as f:
    f.write(section1)

# 3. Continue with more sections
section2 = '''-- Section 2
INSERT INTO table2 ...
'''
with open('/path/to/file.sql', 'a') as f:
    f.write(section2)
```

#### Benefits

1. **Error Isolation**: If a syntax error occurs, it's easier to identify which section caused it
2. **Memory Efficiency**: Each chunk is processed independently
3. **Progress Tracking**: You can verify each section is written correctly
4. **Maintainability**: Easier to update specific sections without touching the entire file

## Database Development

### Schema Management

1. **Schema Files**: Located in `/root/valkyrie/data/`
   - `schema.sql`: Main database schema with tables, indexes, and constraints
   - `sample_data.sql`: Test data for development and testing

2. **Running Database Setup**:
   ```bash
   # Create database
   createdb valkyrie_dev

   # Apply schema
   psql -d valkyrie_dev -f data/schema.sql

   # Load sample data
   psql -d valkyrie_dev -f data/sample_data.sql
   ```

3. **Database Models**: SQLAlchemy models in `src/models/`
   - `job.py`: Job tracking and configuration
   - `company.py`: Company master data management
   - `record.py`: Data processing records
   - `audit_log.py`: Comprehensive audit trail

### API Development

1. **FastAPI Structure**:
   - Routers in `src/api/routes/`
   - Schemas in `src/schemas/`
   - Services in `src/services/`

2. **Authentication**: JWT-based authentication with secure password hashing

3. **LLM Integration**: 
   - Gemini API for data enrichment
   - Configurable via environment variables
   - Async processing for better performance

### Testing

1. **Unit Tests**: Use pytest for all components
2. **Integration Tests**: Test API endpoints with test database
3. **Load Tests**: Verify performance with concurrent requests

### Environment Setup

1. **Required Environment Variables**:
   ```bash
   DATABASE_URL=postgresql://user:pass@localhost/valkyrie_dev
   GEMINI_API_KEY=your-api-key
   JWT_SECRET_KEY=your-secret-key
   ```

2. **Python Environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

### Code Style

1. **Python**: Follow PEP 8, use type hints
2. **SQL**: Use uppercase for keywords, lowercase for identifiers
3. **Comments**: Document complex logic and business rules

### Git Workflow

1. **Branches**: 
   - `main`: Production-ready code
   - `develop`: Integration branch
   - `feature/*`: New features
   - `fix/*`: Bug fixes

2. **Commits**: Use conventional commit messages
   - `feat:` New features
   - `fix:` Bug fixes
   - `docs:` Documentation updates
   - `refactor:` Code refactoring

### Performance Considerations

1. **Database**:
   - Use indexes on frequently queried columns
   - JSONB GIN indexes for enrichment data
   - Connection pooling for concurrent requests

2. **API**:
   - Async endpoints for I/O operations
   - Pagination for large result sets
   - Caching for frequently accessed data

3. **LLM Processing**:
   - Batch processing for efficiency
   - Rate limiting to avoid API limits
   - Error handling with exponential backoff
