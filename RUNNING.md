# NyayaVault Running Guide

This guide runs the complete NyayaVault stack on Windows, macOS, or Linux.

## Requirements

Install:

- Docker Desktop with the Docker engine running
- Git
- Python 3.10 or newer for optional local backend development
- Node.js 20 or newer for optional local frontend development

NyayaVault uses Supabase PostgreSQL for the application database. PostgreSQL is not started by Docker Compose.

## First-Time Setup

### 1. Configure Supabase

Copy the backend environment template:

```powershell
cd backend
Copy-Item .env.example .env
```

Edit `backend/.env` and set:

```env
DATABASE_URL=postgresql+asyncpg://postgres.<project-ref>:<database-password>@<pooler-host>:6543/postgres
SUPABASE_URL=https://<project-ref>.supabase.co
SUPABASE_ANON_KEY=<supabase-anon-key>
SECRET_KEY=<long-random-secret>
```

Use the Supabase transaction pooler connection string from the Supabase Connect dialog. The URL must use `postgresql+asyncpg://` and normally port `6543`.

Do not commit `backend/.env` or expose database passwords, Supabase keys, JWT secrets, or API keys.

### 2. Provision the database

Open the Supabase SQL Editor and run:

```text
backend/supabase_bootstrap.sql
```

Database provisioning is explicit. The FastAPI application does not create tables or seed data during startup.

The bootstrap administrator is:

```text
Email: admin@nyayavault.gov.in
Password: NyayaVault@2026
```

Change the password after the first login.

### 3. Check Docker

Start Docker Desktop, then from the repository root run:

```powershell
cd D:\Hackathons\NyayaVault
docker info
```

If `docker info` fails, start or restart Docker Desktop before continuing.

## Run Everything With Docker

From the repository root:

```powershell
docker compose up --build -d
```

This starts:

- React/Vite frontend
- FastAPI backend
- MinIO object storage
- MinIO bucket initializer
- Qdrant
- Redis

Supabase PostgreSQL remains external and is read from `backend/.env`.

Check service status:

```powershell
docker compose ps
```

View backend logs:

```powershell
docker compose logs -f backend
```

View all logs:

```powershell
docker compose logs -f
```

Open the application:

- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- Swagger: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- MinIO Console: http://localhost:9001
- Qdrant dashboard: http://localhost:6333/dashboard

Local MinIO credentials:

```text
Username: minioadmin
Password: minioadmin
```

The Compose initializer creates these buckets:

- `nyayavault-documents`: live document and certificate objects
- `nyayavault-canonical`: canonical copies used for integrity restoration

## Verify the Application

### Backend health

```powershell
Invoke-WebRequest -UseBasicParsing http://localhost:8000/api/v1/health
Invoke-WebRequest -UseBasicParsing http://localhost:8000/api/v1/health/db
Invoke-WebRequest -UseBasicParsing http://localhost:8000/api/v1/health/storage
```

The database and storage health responses should report `UP`.

### Login

Use the bootstrap administrator credentials in the frontend, or call the API:

```powershell
$body = @{ email = "admin@nyayavault.gov.in"; password = "NyayaVault@2026" } | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri http://localhost:8000/api/v1/auth/login -ContentType "application/json" -Body $body
```

### Upload verification

1. Log in at http://localhost:5173.
2. Open **Documents**.
3. Select a case and upload a document.
4. Open http://localhost:9001.
5. Open `nyayavault-documents` and locate the object under:

```text
cases/{case_id}/documents/{document_id}/versions/{version_id}/{filename}
```

6. Open `nyayavault-canonical` and confirm the same key exists there.
7. Verify the object metadata includes `sha256`; the canonical object also includes `canonical=true`.

The application uses MinIO internally at `http://minio:9000`. Presigned URLs use `http://localhost:9000` so they can be opened by the browser on the host machine.

## Stop and Reset

Stop containers but keep persistent volumes:

```powershell
docker compose down
```

Stop containers and delete MinIO, Qdrant, and Redis data:

```powershell
docker compose down -v
```

Do not use `down -v` if you need to preserve uploaded local MinIO objects.

## Local Development Without Docker

Run MinIO, Qdrant, and Redis with Docker:

```powershell
docker compose up -d minio minio-init qdrant redis
```

Run the backend in a separate terminal:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

For this mode, use these local endpoints in `backend/.env`:

```env
STORAGE_ENDPOINT=http://localhost:9000
STORAGE_PUBLIC_ENDPOINT=http://localhost:9000
QDRANT_URL=http://localhost:6333
REDIS_URL=redis://localhost:6379/0
```

Run the frontend in another terminal:

```powershell
cd frontend
npm install
npm run dev
```

## Tests and Builds

Backend syntax and tests:

```powershell
cd backend
python -m compileall -q .\app .\tests
$env:TEST_DATABASE_URL="postgresql+asyncpg://<test-user>:<test-password>@<test-pooler-host>:6543/postgres"
python -m pytest tests/test_api.py -v
```

Tests require an isolated database and must not use the production Supabase database.

Frontend production build:

```powershell
cd frontend
npm install
npm run build
```

Compose validation:

```powershell
cd D:\Hackathons\NyayaVault
docker compose config --quiet
```

## Troubleshooting

### `docker ps` is empty

Check Docker Desktop and run:

```powershell
docker info
docker compose up --build -d
docker compose ps
```

### MinIO buckets are empty

Check the initializer:

```powershell
docker compose logs minio-init
docker compose logs backend
```

The backend must report `STORAGE_ENDPOINT=http://minio:9000` when running in Compose. The upload must return HTTP `201`.

### Login returns database errors

Check that:

- `backend/.env` has a valid Supabase pooler URL.
- The URL uses `postgresql+asyncpg://`.
- The pooler port is `6543`.
- `backend/supabase_bootstrap.sql` has been run.
- The backend can reach `/api/v1/health/db`.

### Presigned downloads use `minio:9000`

When the backend runs in Docker, set:

```env
STORAGE_PUBLIC_ENDPOINT=http://localhost:9000
```

The internal endpoint remains:

```env
STORAGE_ENDPOINT=http://minio:9000
```

### Inspect MinIO from PowerShell

Use the MinIO client container on the Compose network:

```powershell
docker run --rm --network nyayavault_default --entrypoint /bin/sh minio/mc:latest -c "mc alias set local http://minio:9000 minioadmin minioadmin && mc ls --recursive local/nyayavault-documents"
```

PowerShell does not provide Unix `grep` by default. Use `Select-String` instead:

```powershell
docker exec nyayavault-minio-1 env | Select-String MINIO
```
