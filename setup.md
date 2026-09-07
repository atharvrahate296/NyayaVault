# NyayaVault — Complete System & Qdrant Setup Guide

This guide provides step-by-step instructions for running the complete **NyayaVault** stack locally, including setting up and verifying a **Qdrant Vector Database instance running on Docker**, configuring environment credentials, and launching the FastAPI backend and React frontend.

---

## Table of Contents

1. [Prerequisites](#1-prerequisites)
2. [Environment Configuration (`.env`)](#2-environment-configuration-env)
3. [Qdrant Setup via Docker](#3-qdrant-setup-via-docker)
   - [Method 1: Standalone Docker Container (Recommended for Local Dev)](#method-1-standalone-docker-container-recommended-for-local-dev)
   - [Method 2: Docker Compose (Full Stack Orchestration)](#method-2-docker-compose-full-stack-orchestration)
   - [Verifying Qdrant Connection & Web Dashboard](#verifying-qdrant-connection--web-dashboard)
   - [Configuring Vector Collections & Dimensions](#configuring-vector-collections--dimensions)
4. [Infrastructure Services Setup](#4-infrastructure-services-setup)
   - [PostgreSQL (Relational Database)](#postgresql-relational-database)
   - [MinIO (Object Storage)](#minio-object-storage)
   - [Redis (Task Broker & Cache)](#redis-task-broker--cache)
5. [Backend Setup (FastAPI + AI Services)](#5-backend-setup-fastapi--ai-services)
6. [Frontend Setup (React + Vite)](#6-frontend-setup-react--vite)
7. [Default Application & Service Credentials](#7-default-application--service-credentials)
8. [Troubleshooting & FAQ](#8-troubleshooting--faq)

---

## 1. Prerequisites

Ensure your development machine has the following tools installed:

| Tool | Recommended Version | Purpose |
|---|---|---|
| **Docker Desktop** | 24.0+ | Container engine for Qdrant, Postgres, MinIO, Redis |
| **Docker Compose** | v2.20+ | Multi-container stack execution |
| **Python** | 3.11+ | FastAPI backend and AI pipelines |
| **Node.js** | 18.0+ | React + Vite frontend environment |
| **npm** | 9.0+ | Package manager for frontend dependencies |

Verify Docker is active:
```bash
docker --version
docker compose version
```

---

## 2. Environment Configuration (`.env`)

All secret keys, API credentials, and database connections are loaded **exclusively** from `backend/.env`.

### Step 1: Create your local `.env` file
Copy the `.env.example` template:
```bash
cp backend/.env.example backend/.env
```

### Step 2: Key Environment Variables Explained
Open `backend/.env` in your text editor and review the parameters:

```env
# Application Environment
APP_ENV=development
APP_NAME=NyayaVault
APP_VERSION=1.0.0
DEBUG=true
SECRET_KEY=nyayavault-dev-secret-change-in-production-minimum-32-chars

# Relational Database (Supabase PostgreSQL)
DATABASE_URL=postgresql+asyncpg://<username>:<password>@<pooler-host>:6543/<database-name>


# JWT Secrets
JWT_SECRET=nyayavault-jwt-secret-dev-change-in-production
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=120
REFRESH_TOKEN_EXPIRE_DAYS=7

# Object Storage (MinIO)
STORAGE_PROVIDER=minio
STORAGE_ENDPOINT=http://localhost:9000
STORAGE_ACCESS_KEY=minioadmin
STORAGE_SECRET_KEY=minioadmin
STORAGE_BUCKET=nyayavault-documents

# Qdrant Vector Database Credentials & Endpoints
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=
QDRANT_COLLECTION_DOCUMENTS=nyayavault_documents
QDRANT_COLLECTION_SECURITY=nyayavault_security
QDRANT_VECTOR_SIZE=384

# Task Queue & Broker (Redis)
REDIS_URL=redis://localhost:6379/0

# AI, OCR & Vector Embedding Engines
AI_MODE=mock                        # Options: mock, local, cloud
AI_CONFIDENCE_THRESHOLD=70          # Confidence threshold (0-100)
OCR_ENGINE=mock                     # Options: mock, tesseract, easyocr
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
SPACY_MODEL=en_core_web_sm

# External API Keys (Optional for Cloud AI / LLM Inference)
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=llama-3.3-70b-versatile
```



> **Security Note:** Never commit `backend/.env` to version control. Keep `.env.example` updated whenever new credentials or secrets are introduced.

---

## 3. Qdrant Setup via Docker

Qdrant stores document vector embeddings, extracted entity payloads, AI search indexes, and behavioral anomaly vectors for tamper risk analysis.

### Method 1: Standalone Docker Container (Recommended for Local Dev)

To launch a dedicated Qdrant container with persistent storage:

```bash
docker run -d \
  --name nyayavault-qdrant \
  -p 6333:6333 \
  -p 6334:6334 \
  -v qdrant_storage:/qdrant/storage \
  qdrant/qdrant:latest
```

- **Port `6333`**: REST API & Web Dashboard
- **Port `6334`**: gRPC API
- **Volume `qdrant_storage`**: Persists vector indexes across container restarts.

#### Running with Custom Storage Directory (Local Folder)
If you prefer mounting a local folder in your project directory:
```bash
docker run -d \
  --name nyayavault-qdrant \
  -p 6333:6333 \
  -p 6334:6334 \
  -v ./qdrant_data:/qdrant/storage \
  qdrant/qdrant:latest
```

---

### Method 2: Docker Compose (Full Stack Orchestration)

The repository's `docker-compose.yml` comes pre-configured with Qdrant and Redis services.

Start all services (Frontend, Backend, Postgres, MinIO, Qdrant, Redis) with a single command:

```bash
docker compose up -d --build
```

In `docker-compose.yml`, Qdrant is configured as follows:
```yaml
  qdrant:
    image: qdrant/qdrant:latest
    restart: always
    ports:
      - "6333:6333"   # REST API & Web Dashboard
      - "6334:6334"   # gRPC API
    volumes:
      - qdrant_data:/qdrant/storage
    environment:
      QDRANT__SERVICE__GRPC_PORT: 6334
```

When running in Docker Compose, update `backend/.env` or container environment:
```env
QDRANT_URL=http://qdrant:6333
```

---

### Verifying Qdrant Connection & Web Dashboard

#### 1. REST Health Check
Run the following curl command in your terminal:
```bash
curl http://localhost:6333/healthz
```
**Expected Response:**
```json
{"title":"qdrant - vector search engine","version":"1.x.x"}
```

#### 2. Web Dashboard
Open your browser and navigate to:
[http://localhost:6333/dashboard](http://localhost:6333/dashboard)

The Qdrant dashboard allows you to visually inspect collections, payload indexes, and vector points.

#### 3. Test Python Qdrant Client Connection
You can test connection directly from Python:
```python
from qdrant_client import QdrantClient

client = QdrantClient(url="http://localhost:6333")
print("Qdrant Collections:", client.get_collections())
```

---

### Configuring Vector Collections & Dimensions

The NyayaVault backend automatically creates required collections upon startup.

Ensure your `QDRANT_VECTOR_SIZE` matches your configured `EMBEDDING_MODEL`:

| Embedding Model | Vector Dimension (`QDRANT_VECTOR_SIZE`) |
|---|---|
| `sentence-transformers/all-MiniLM-L6-v2` (Default Local) | `384` |
| `sentence-transformers/all-mpnet-base-v2` | `768` |
| OpenAI `text-embedding-3-small` | `1536` |
| OpenAI `text-embedding-3-large` | `3072` |

---

## 4. Infrastructure Services Setup

### Supabase (Relational Database)

NyayaVault uses **Supabase** as its managed PostgreSQL database. No local Postgres container is needed.

#### Step 1: Configure your Supabase credentials in `backend/.env`

```env
# Connection pooler URL (Transaction mode — required for asyncpg)
DATABASE_URL=postgresql+asyncpg://<user>:<password>@<host>:6543/postgres?prepared_statement_cache_size=0

SUPABASE_URL=https://<your-project-id>.supabase.co
SUPABASE_ANON_KEY=<your-supabase-anon-key>
```

Find these values in your Supabase project dashboard under **Settings → Database → Connection string (Transaction pooler)**.

#### Step 2: Apply the schema bootstrap script

Open your **Supabase SQL Editor** and run the contents of:

```
backend/supabase_bootstrap.sql
```

This script is **idempotent** — safe to re-run at any time. It creates all 26 tables, 41 indexes, 6 updated_at triggers, and seeds static reference data (roles, permissions, default admin account).

#### Step 3: Verify connectivity

Once the backend is running, call:
```bash
curl http://localhost:8000/api/v1/health/db
```
Expected response:
```json
{"status": "UP", "database": "CONNECTED", "url_type": "postgresql+asyncpg"}
```

> **Note:** The backend does not seed data on startup. Run `python seed.py` manually from `backend/` when demo data is required.

---

### MinIO (Object Storage)

Run MinIO in Docker:
```bash
docker run -d \
  --name nyayavault-minio \
  -e MINIO_ROOT_USER=minioadmin \
  -e MINIO_ROOT_PASSWORD=minioadmin \
  -p 9000:9000 \
  -p 9001:9001 \
  minio/minio:latest \
  server /data --console-address ":9001"
```

- **S3 Endpoint:** `http://localhost:9000`
- **Web Console:** [http://localhost:9001](http://localhost:9001) (User: `minioadmin`, Password: `minioadmin`)

---

### Redis (Task Broker & Cache)

Run Redis in Docker:
```bash
docker run -d \
  --name nyayavault-redis \
  -p 6379:6379 \
  redis:7-alpine
```

Verify Redis:
```bash
docker exec -it nyayavault-redis redis-cli ping
# Output: PONG
```

---

## 5. Backend Setup (FastAPI + AI Services)

### Step 1: Navigate to Backend Directory
```bash
cd backend
```

### Step 2: Create Virtual Environment
```bash
python -m venv .venv
```
Activate environment:
- **Windows (PowerShell):** `.\.venv\Scripts\Activate.ps1`
- **macOS / Linux:** `source .venv/bin/activate`

### Step 3: Install Dependencies
```bash
pip install -r requirements.txt
```

#### Install AI & ML Libraries (for non-mock execution):
```bash
pip install qdrant-client sentence-transformers spacy pytesseract easyocr opencv-python-headless scikit-learn
python -m spacy download en_core_web_sm
```

### Step 4: Launch FastAPI Server
```bash
uvicorn app.main:app --reload --port 8000
```

- **API Base:** [http://localhost:8000](http://localhost:8000)
- **Interactive Swagger Docs:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc Documentation:** [http://localhost:8000/redoc](http://localhost:8000/redoc)

---

## 6. Frontend Setup (React + Vite)

### Step 1: Navigate to Frontend Directory
```bash
cd frontend
```

### Step 2: Install Node Modules
```bash
npm install
```

### Step 3: Start Development Server
```bash
npm run dev
```

- **Frontend URL:** [http://localhost:5173](http://localhost:5173)

---

## 7. Default Application & Service Credentials

### User Role Accounts (Provisioned explicitly)

| Role | Email | Password |
|---|---|---|
| **System Admin** | `admin@nyayavault.gov.in` | `NyayaVault@2026` |
| **Investigating Officer** | `investigator@nyayavault.gov.in` | `NyayaVault@2026` |
| **Forensic Staff** | `forensics@nyayavault.gov.in` | `NyayaVault@2026` |
| **Senior Officer** | `senior@nyayavault.gov.in` | `NyayaVault@2026` |

> The administrator is created by `supabase_bootstrap.sql`. The remaining demo accounts are added only when an operator runs `python seed.py` from `backend/`.

### Infrastructure Credentials

| Service | Connection / Auth |
|---|---|
| **Supabase** | Configure `DATABASE_URL` in `backend/.env` from Supabase dashboard |
| **MinIO** | User: `minioadmin` \| Pass: `minioadmin` \| Console Port: `9001` |
| **Qdrant** | REST: `http://localhost:6333` \| gRPC: `6334` \| Dashboard: `http://localhost:6333/dashboard` |
| **Redis** | Endpoint: `localhost:6379` |

---

## 8. Troubleshooting & FAQ

### Qdrant container exits or fails to start
- **Cause:** Port `6333` or `6334` already in use by another application.
- **Fix:** Map host ports, e.g., `-p 16333:6333 -p 16334:6334`, and update `QDRANT_URL=http://localhost:16333` in `.env`.

### Vector size mismatch error (`Wrong vector size`)
- **Cause:** Collection created with vector size 384, but model produces 768 dimensions.
- **Fix:** Delete collection in `http://localhost:6333/dashboard`, update `QDRANT_VECTOR_SIZE=768` in `backend/.env`, and restart backend.

### spaCy model missing error (`OSError: Can't find model 'en_core_web_sm'`)
- **Fix:** Run inside active virtual environment:
  ```bash
  python -m spacy download en_core_web_sm
  ```

### Tesseract OCR error (`tesseract is not installed or it's not in your PATH`)
- **Fix:** Install Tesseract binary on host system or set `OCR_ENGINE=mock` in `backend/.env` for local testing.
