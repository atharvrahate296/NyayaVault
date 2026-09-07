# NyayaVault - Secure Digital Document Management System

> **Ministry of Home Affairs | National Crime Records Bureau (NCRB) | Women Safety Division**  
> **Problem Statement:** Secure Digital Document Management System for Legal and Investigation Documents  
> **Theme:** Blockchain & Cybersecurity  

NyayaVault is an enterprise-grade, blockchain-anchored, tamper-evident digital document and evidence management platform built for law-enforcement agencies, forensic laboratories, courts, and investigative officers handling sensitive legal and investigation records.

---

## ✨ Key System Capabilities

- 🍱 **Modern Bento Dashboard:** Sleek enterprise Bento-grid layout with real-time Hyperledger Fabric sentinel metrics, system integrity ratios, active dossiers, AI classification queues, and live audit ledger streams.
- 📂 **Collapsible Sidebar Navigation:** Responsive left navbar featuring an icon-only collapsed state (`w-20`) with floating tooltips and glowing indicators, and an expanded state (`w-64`) with persistent `localStorage` state.
- 🛡️ **Cryptographic Integrity & Tamper Sentinel:** Continuous SHA-256 hash verification, live tamper simulation, and cryptographic restoration against blockchain-anchored proofs.
- 📜 **Section 65B Evidence Act Certificates:** Instant ReportLab-powered PDF generation certifying electronic records under Section 65B of the Indian Evidence Act / Bharatiya Sakshya Adhiniyam (BSA).
- ⛓️ **Cryptographic Chain of Custody:** Immutable timeline tracking every evidence transfer, custodian handover, laboratory dispatch, and forensic observation.
- 🤖 **AI Pipeline & Human Review:** Automated OCR text extraction, automated document type classification, entity extraction (PII/sensitive identifiers), and human review queue.
- 🔒 **Dynamic Access Control (ABAC & RBAC):** 4-tier security clearance matrix (Confidential, Secret, Top Secret), dynamic attribute-based access control, and break-glass emergency overrides.
- 📡 **Security Monitoring & Threat Radar:** Automated anomaly detection, suspicious download alerts, off-hours access monitoring, and immediate IP blocking.
- 📊 **Real-Time Operational Analytics:** Case status distribution, document ingestion trends, integrity health indices, and court-admissibility metrics.

---

## 🏛️ Project Architecture

The repository is organized into independent, loosely coupled `frontend` and `backend` services:

```text
Nyayavault/
├── frontend/                     # React 19 + Tailwind CSS + Lucide Icons + Vite
│   ├── src/
│   │   ├── components/           # Bento Layout, Collapsible Sidebar, UI primitives
│   │   │   ├── Layout.jsx        # Bento collapsible sidebar layout & header
│   │   │   └── ui/               # Bento Card, MetricCard, Table, Badge, Button, PageHeader
│   │   ├── pages/                # 15 domain-specific route views
│   │   │   ├── Dashboard.jsx     # Modular Bento Dashboard with live metrics
│   │   │   ├── Cases.jsx         # Case registry, dossiers, and investigator assignments
│   │   │   ├── Documents.jsx     # Document repository, versioning, and uploads
│   │   │   ├── Evidence.jsx      # Digital & physical evidence vault
│   │   │   ├── Custody.jsx       # Cryptographic Chain of Custody timeline
│   │   │   ├── Integrity.jsx     # SHA-256 hash verification & tamper simulation
│   │   │   ├── Signatures.jsx    # Digital signature signing & verification
│   │   │   ├── AuditLedger.jsx   # Tamper-evident hash-chained audit log
│   │   │   ├── Security.jsx      # Threat radar, anomaly alerts & session monitors
│   │   │   ├── Certificates.jsx  # Section 65B PDF certificate generation
│   │   │   ├── AIReview.jsx      # OCR queue, entity extraction & approval workflow
│   │   │   ├── AccessControl.jsx # ABAC policies & emergency break-glass control
│   │   │   ├── Users.jsx         # User directory & clearance management
│   │   │   ├── Analytics.jsx     # Operational intelligence & charts
│   │   │   └── Settings.jsx      # System configuration & subsystem health
│   │   ├── api/                  # Axios/Fetch API client wired to FastAPI backend
│   │   └── index.css             # Tailwind CSS design system & Bento styles
│   ├── package.json              # Frontend dependencies
│   ├── vite.config.js            # Vite build configuration
│   └── Dockerfile                # Frontend container configuration
│
├── backend/                      # Python FastAPI + SQLAlchemy + Supabase PostgreSQL + MinIO + Qdrant

│   ├── app/
│   │   ├── main.py               # FastAPI entrypoint, CORS, and lifespan startup
│   │   ├── config/               # Pydantic Settings & environment config
│   │   ├── core/                 # JWT security, password hashing, RBAC, exceptions
│   │   ├── db/                   # Async SQLAlchemy engine, models, and seed data
│   │   ├── api/v1/               # Master API router uniting all 23 backend modules
│   │   ├── modules/
│   │   │   ├── auth/             # Login, token refresh, logout, profile
│   │   │   ├── users/            # User CRUD & active status management
│   │   │   ├── roles/            # RBAC roles & permissions
│   │   │   ├── policies/         # ABAC policy evaluation engine
│   │   │   ├── cases/            # Case management & officer assignments
│   │   │   ├── documents/        # File upload, versioning, secure download
│   │   │   ├── storage/          # MinIO/S3 private object storage
│   │   │   ├── integrity/        # SHA-256 verification, tamper simulation & restoration
│   │   │   ├── blockchain/       # Hyperledger Fabric transaction recording & ledger
│   │   │   ├── ai/               # OCR, classification, entity extraction & human review
│   │   │   ├── search/           # Keyword, semantic, and hybrid search
│   │   │   ├── evidence/         # Evidence registry & custody tracking
│   │   │   ├── custody/          # Cryptographically chained custody events
│   │   │   ├── signatures/       # Digital signature workflows & verification
│   │   │   ├── audit/            # Tamper-evident hash-chained audit logging
│   │   │   ├── security_monitoring/ # Anomaly detection & security alerts
│   │   │   ├── certificates/     # ReportLab Section 65B Certificate PDF generation
│   │   │   ├── notifications/    # Alert & system notifications
│   │   │   ├── analytics/        # Real-time operational intelligence dashboard
│   │   │   └── health/           # Liveness & subsystem observability probes
│   │   ├── workers/              # Asynchronous background job processor
│   │   └── integrations/         # CCTNS, e-Courts, and DigiLocker gateways
│   ├── tests/                    # Pytest test suite covering core workflows
│   ├── requirements.txt          # Python backend dependencies
│   ├── Dockerfile                # Backend container configuration
│
├── docker-compose.yml            # Orchestration for Frontend, Backend, MinIO, Qdrant, and Redis
├── RUNNING.md                    # Complete setup, run, verification, and troubleshooting guide
├── .gitignore                    # Git ignore rules for Python, Node, SQLite, and env
├── Nyayavault - PRD.md           # Product Requirement Document
└── Nyayavault Backend Technical - PRD.md # Backend Technical Architecture Specification
```

---

## 🚀 Quick Start Guide

### Option A: Run via Docker Compose (Recommended)

Spins up the frontend, backend, MinIO S3-compatible object storage, Qdrant, and Redis. PostgreSQL is hosted by Supabase and is configured through `backend/.env`.

For the complete setup and troubleshooting instructions, see [RUNNING.md](RUNNING.md).

```bash
docker compose up --build -d
```

- **Frontend UI:** `http://localhost:5173`
- **Backend API:** `http://localhost:8000`
- **Interactive Swagger Docs:** `http://localhost:8000/docs`
- **Interactive ReDoc:** `http://localhost:8000/redoc`
- **MinIO Console:** `http://localhost:9001` (User: `minioadmin` / Pass: `minioadmin`)
- **Qdrant Dashboard:** `http://localhost:6333/dashboard`

Check the stack with:

```bash
docker compose ps
docker compose logs -f backend
```

Stop it with:

```bash
docker compose down
```

---

### Option B: Local Development Setup

#### 1. Backend Setup (FastAPI)

```bash
cd backend

# Create and activate virtual environment
python -m venv .venv
# On Windows (PowerShell):
.\.venv\Scripts\activate
# On Linux/macOS:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the development server
uvicorn app.main:app --reload --port 8000
```

> **Database provisioning is explicit:**  
> The backend does not create tables or seed users when it starts. Run [`backend/supabase_bootstrap.sql`](backend/supabase_bootstrap.sql) in the Supabase SQL Editor first. Tests must use a separate isolated PostgreSQL database through `TEST_DATABASE_URL`.

#### 2. Run Backend Tests

```bash
cd backend
python -m pytest tests/test_api.py -v
```

#### 3. Frontend Setup (React + Vite)

```bash
cd frontend

# Install Node dependencies
npm install

# Start Vite dev server
npm run dev
```

The frontend application will be live at `http://localhost:5173`.

### Supabase PostgreSQL Setup

The backend uses SQLAlchemy to connect directly to Supabase PostgreSQL. Configure the backend `.env` with the Supabase database connection string, not only the project URL and anon key:

```env
DATABASE_URL=postgresql+asyncpg://postgres:<database-password>@<project-ref>.pooler.supabase.com:6543/postgres
SECRET_KEY=<long-random-jwt-secret>
SUPABASE_URL=https://<project-ref>.supabase.co
SUPABASE_ANON_KEY=<supabase-anon-key>
```

The anon key is not used for administrator approval or database writes. Keep the database password and JWT secret server-side.

Before starting the backend, open the Supabase SQL Editor and run [`backend/supabase_bootstrap.sql`](backend/supabase_bootstrap.sql). This script creates the current application schema, roles, permissions, and the initial administrator account. It is idempotent and can be safely rerun.

The bootstrap administrator is:

```text
Email: admin@nyayavault.gov.in
Password: NyayaVault@2026
```

Change the administrator password after the first login. The API itself does not create tables, insert demo users, or alter the database during startup.

### Account Request and Approval Workflow

1. An applicant submits `POST /api/v1/auth/signup` for Investigating Officer, Forensic Staff, or Senior Officer.
2. The request is stored as `PENDING`; no login account is created yet.
3. The seeded administrator (`admin@nyayavault.gov.in`) signs in and reviews `GET /api/v1/auth/registration-requests`.
4. The administrator approves or rejects the request using the corresponding `/approve` or `/reject` endpoint.
5. Approval creates the active user with role-derived clearance. Only then can the applicant sign in.

The frontend provides `/signup`, `/login`, and the administrator-only `/registration-requests` screen for testing this workflow.

---

## 🔐 Default User Accounts & Clearances

| Role | Email | Password | Clearance Level | Permitted Operations |
|---|---|---|---|---|
| **System Administrator** | `admin@nyayavault.gov.in` | `NyayaVault@2026` | Level 4 (Top Secret) | Full System Access, User Admin, Audit Logs |
| **Investigating Officer** | `investigator@nyayavault.gov.in` | `NyayaVault@2026` | Level 3 (Secret) | Case Files, Evidence Ingestion, 65B Generation |
| **Forensic Staff** | `forensics@nyayavault.gov.in` | `NyayaVault@2026` | Level 3 (Secret) | Chain of Custody, Hash Verification, Lab Notes |
| **Senior Officer** | `senior@nyayavault.gov.in` | `NyayaVault@2026` | Level 4 (Top Secret) | Dossier Sign-offs, Security Overrides, Analytics |

---

## 🗺️ Application Route Overview

| Route | View | Description |
|---|---|---|
| `/` | **Bento Dashboard** | Operational command center with Hyperledger sentinel and KPI tiles |
| `/cases` | **Cases** | FIR & Crime dossier registry with assigned investigating officers |
| `/documents` | **Documents** | Secure legal vault with automated version tracking and downloads |
| `/evidence` | **Evidence Registry** | Digital and physical evidence records with seal verification |
| `/custody` | **Chain of Custody** | Cryptographic custody timeline with custody handover events |
| `/integrity` | **Integrity Sentinel** | SHA-256 verification, live tamper simulation & one-click restoration |
| `/signatures` | **Digital Signatures** | PKI digital signing and tamper-evident certificate validation |
| `/audit` | **Audit Ledger** | Append-only hash-chained ledger logging all platform actions |
| `/security` | **Security Radar** | Anomaly detection, suspicious activity alerts & IP blocking |
| `/certificates` | **65B Certificates** | Indian Evidence Act Sec 65B PDF certificate generation |
| `/ai-review` | **AI Review Queue** | OCR text extraction, PII entity masking, and document review |
| `/access-control` | **Access Control** | Attribute-based access policies (ABAC) & break-glass emergency mode |
| `/users` | **User Management** | Officer directory, role assignments, and clearance levels |
| `/analytics` | **Analytics** | Graphical insights on case progress, evidence volume & security |
| `/settings` | **System Health** | Node status, database connections, and storage probes |

---

## 🛡️ Security & Compliance Standards

- **Indian Evidence Act / BSA Compliance:** Electronic record admissibility under Section 65B / Section 63 BSA.
- **Cryptographic Hashing:** SHA-256 / Merkle tree verification anchored to Hyperledger Fabric transaction blocks.
- **Role & Attribute-Based Access Control:** Dual-layer RBAC + ABAC enforcement with strict clearance tiering.
- **Tamper Evidence:** Cryptographically hash-chained audit trails preventing silent log alteration.
