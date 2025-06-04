# RAGFlow MVP

RAGFlow processes Gmail and Google Drive content for the Indian Valve Company.  It stores emails and documents in a local database and produces a daily email summary.

## Quick start

```bash
bash setup.sh
docker compose up -d --build
```

### Services

| Service    | Port | Purpose             |
|------------|------|---------------------|
| backend    | 8000 | API server          |
| worker     | -    | Background tasks    |
| frontend   | 8080 | Search interface    |
| RAGFlow    | 3000 | Vector store        |
| Ollama     | 11434| Local language model|
| PostgreSQL | 5432 | Data storage        |
| Redis      | 6379 | Job queue           |

### Authentication

1. Open `/auth/login` in a browser.
2. Authorize each inbox.
3. Confirm status at `/auth/status`.

### Usage

```
POST /ingest/emails          # fetch new emails
POST /api/documents/upload   # process drive files
POST /api/digest/daily       # send the daily digest
```

API documentation is at `http://localhost:8000/docs`.
