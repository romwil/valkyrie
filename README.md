# Project Valkyrie: LLM-Driven Data Action Platform

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104.1-009688.svg)](https://fastapi.tiangolo.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## 🎯 Overview

Project Valkyrie is a Proof of Concept (POC) demonstrating **LLM-First Ambiguity Resolution** in sales data enrichment. The system intelligently classifies, cleans, and consolidates person-level titles and company firmographics from Apollo/Augmentation data.

### Key Features

- **LLM-First Title Resolution**: Resolves title collisions and extrapolates formal titles from ambiguous/vanity text
- **Company MDM Flagging**: Differentiates True Job Changes from Company Data Updates
- **Asynchronous Processing**: High-performance API with concurrent worker pool
- **Web UI**: Responsive interface for file upload, status monitoring, and output download
- **Standardized Outputs**: Generates actionable data analysis and unified firmographics reports

## 🏗️ Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────────┐
│   Web UI    │────▶│  FastAPI     │────▶│  Worker Pool    │
│  (React)    │     │  Backend     │     │ (ThreadExecutor)│
└─────────────┘     └──────────────┘     └─────────────────┘
                            │                      │
                            ▼                      ▼
                    ┌──────────────┐      ┌─────────────┐
                    │ Status Files │      │ Gemini API  │
                    └──────────────┘      └─────────────┘
```

## 📋 Requirements

- Python 3.8+
- Gemini API Key (for LLM processing)
- 4GB+ RAM recommended

## 🚀 Quick Start

1. **Clone the repository**
   ```bash
   git clone https://github.com/romwil/valkyrie.git
   cd valkyrie
   ```

2. **Set up environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Configure environment variables**
   ```bash
   cp .env.example .env
   # Edit .env and add your GEMINI_API_KEY
   ```

4. **Run the application**
   ```bash
   # Start the backend API
   uvicorn api.main:app --reload --port 8000
   
   # In another terminal, start the web UI
   cd web-ui
   npm install
   npm run dev
   ```

5. **Access the application**
   - API: http://localhost:8000
   - Web UI: http://localhost:3000
   - API Docs: http://localhost:8000/docs

## 📊 Data Processing Logic

### LLM Title Resolution Triggers

1. **Scenario A**: New Title Available
   - Title (Input) is Empty AND New Title Value (Apollo) is Not Empty

2. **Scenario B**: Title Collision
   - Title (Input) is Not Empty AND Title (Input) ≠ New Title Value (Apollo)

### Action Flags

- **Update Title**: LLM resolved a clean title
- **Review Title**: LLM returned REVIEW_MANUAL or Augmentation Status is 'Not Matched'
- **Keep Original**: Titles match or no LLM call required
- **True Job Change**: Different companies after normalization
- **Company Data Update**: Same company, matched augmentation

## 📁 Output Files

1. **`[INPUT_PREFIX]_actionable_data_analysis.csv`**
   - Person-level action report
   - Contains all original columns plus action flags

2. **`[INPUT_PREFIX]_unified_firmographics_data.csv`**
   - Company-level consolidation report
   - Aggregated company data with latest values

## 🧪 Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=api --cov=worker

# Run specific test file
pytest tests/test_llm_resolver.py
```

## 🛠️ Development

### Code Quality

```bash
# Format code
black .

# Lint code
flake8

# Type checking
mypy .
```

### Project Structure

```
valkyrie/
├── api/              # FastAPI backend
├── worker/           # Async worker logic
├── web-ui/           # React frontend
├── data/             # Data directories
│   ├── input/        # Upload files
│   ├── output/       # Processed files
│   └── status/       # Job status files
├── tests/            # Test suite
├── docs/             # Documentation
└── valkyrie_config.yaml  # Configuration
```

## ⚙️ Configuration

Edit `valkyrie_config.yaml` to customize:

- File paths and directories
- LLM model settings
- Batch processing parameters
- Encoding configurations

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- Built with FastAPI, React, and Google Gemini
- Designed for high-performance sales data enrichment
- Part of the Life Science Connect ecosystem

---

**Note**: This is a POC. For production use, please ensure proper security measures and API rate limiting.
