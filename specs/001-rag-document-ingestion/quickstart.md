# Quickstart: RAG Document Ingestion Pipeline

## Prerequisites
- [uv](https://github.com/astral-sh/uv) installed
- Docker (for containerization)
- Google Cloud SDK (gcloud) configured

## Local Setup

1. **Navigate to the pipeline directory**:
   ```bash
   cd src/ingestion-pipeline
   ```

2. **Initialize and sync dependencies**:
   ```bash
   uv sync
   ```

3. **Environment Configuration**:
   Copy `.env.example` to `.env` and fill in the values:
   ```bash
   cp .env.example .env
   ```

4. **Run Tests**:
   ```bash
   uv run pytest
   ```

5. **Run Local Worker**:
   ```bash
   uv run uvicorn main:app --reload --port 8080
   ```

## Docker Operations
- **Build**: `docker build -t ingestion-pipeline .`
- **Run**: `docker run -p 8080:8080 --env-file .env ingestion-pipeline`

## Deployment to Cloud Run
```bash
gcloud builds submit --tag gcr.io/YOUR_PROJECT/ingestion-pipeline
gcloud run deploy ingestion-pipeline --image gcr.io/YOUR_PROJECT/ingestion-pipeline --platform managed
```
