-- =============================================================================
-- NyayaVault — Supabase PostgreSQL Bootstrap
-- =============================================================================
-- Run this script ONCE in the Supabase SQL Editor before starting the API.
-- It is fully idempotent — safe to re-run at any time.
--
-- What this script does:
--   1. Enables pgcrypto extension (for bcrypt password hashing in SQL)
--   2. Creates all 26 application tables (CREATE TABLE IF NOT EXISTS)
--   3. Creates all indexes defined in the SQLAlchemy models
--   4. Creates an updated_at trigger function and attaches it to relevant tables
--   5. Seeds static reference data (roles, permissions, role_permissions)
--   6. Seeds the default administrator account
--
-- RLS NOTE: Row Level Security is intentionally left DISABLED on all tables.
-- The FastAPI backend connects via the Supabase Transaction Pooler URL using
-- service-level credentials and enforces all authorization through its own
-- RBAC/ABAC layer. Enabling RLS without matching policies would break the API.
-- =============================================================================

-- ---------------------------------------------------------------------------
-- Extensions
-- ---------------------------------------------------------------------------
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- ---------------------------------------------------------------------------
-- updated_at auto-trigger function
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- ---------------------------------------------------------------------------
-- 1. Identity & RBAC Tables
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS users (
    id               VARCHAR(36)  PRIMARY KEY,
    email            VARCHAR(255) NOT NULL UNIQUE,
    full_name        VARCHAR(255) NOT NULL,
    employee_id      VARCHAR(64)  NOT NULL UNIQUE,
    department       VARCHAR(128) NOT NULL,
    designation      VARCHAR(128) NOT NULL,
    role             VARCHAR(64)  NOT NULL DEFAULT 'Investigating Officer',
    clearance_level  VARCHAR(32)  NOT NULL DEFAULT 'Level 2',
    is_active        BOOLEAN      NOT NULL DEFAULT TRUE,
    password_hash    VARCHAR(255) NOT NULL,
    last_login       TIMESTAMPTZ,
    created_at       TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at       TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_users_email       ON users (email);
CREATE INDEX IF NOT EXISTS idx_users_employee_id ON users (employee_id);

DROP TRIGGER IF EXISTS trg_users_updated_at ON users;
CREATE TRIGGER trg_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();


CREATE TABLE IF NOT EXISTS registration_requests (
    id                       VARCHAR(36)  PRIMARY KEY,
    email                    VARCHAR(255) NOT NULL UNIQUE,
    full_name                VARCHAR(255) NOT NULL,
    employee_id              VARCHAR(64)  NOT NULL UNIQUE,
    department               VARCHAR(128) NOT NULL,
    designation              VARCHAR(128) NOT NULL,
    posting_location         VARCHAR(255) NOT NULL,
    justification            TEXT         NOT NULL,
    requested_role           VARCHAR(64)  NOT NULL,
    password_hash            VARCHAR(255) NOT NULL,
    supporting_document_name VARCHAR(255),
    status                   VARCHAR(16)  NOT NULL DEFAULT 'PENDING',
    approved_by              VARCHAR(36)  REFERENCES users(id),
    approved_at              TIMESTAMPTZ,
    rejection_reason         TEXT,
    created_at               TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at               TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_reg_email       ON registration_requests (email);
CREATE INDEX IF NOT EXISTS idx_reg_employee_id ON registration_requests (employee_id);
CREATE INDEX IF NOT EXISTS idx_reg_role        ON registration_requests (requested_role);
CREATE INDEX IF NOT EXISTS idx_reg_status      ON registration_requests (status);

DROP TRIGGER IF EXISTS trg_reg_requests_updated_at ON registration_requests;
CREATE TRIGGER trg_reg_requests_updated_at
    BEFORE UPDATE ON registration_requests
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();


CREATE TABLE IF NOT EXISTS roles (
    id          VARCHAR(36)  PRIMARY KEY,
    name        VARCHAR(64)  NOT NULL UNIQUE,
    description VARCHAR(255)
);

CREATE INDEX IF NOT EXISTS idx_roles_name ON roles (name);


CREATE TABLE IF NOT EXISTS permissions (
    id          VARCHAR(36)  PRIMARY KEY,
    code        VARCHAR(64)  NOT NULL UNIQUE,
    name        VARCHAR(128) NOT NULL,
    description VARCHAR(255)
);

CREATE INDEX IF NOT EXISTS idx_permissions_code ON permissions (code);


CREATE TABLE IF NOT EXISTS role_permissions (
    id              VARCHAR(36) PRIMARY KEY,
    role_name       VARCHAR(64) NOT NULL,
    permission_code VARCHAR(64) NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_rp_role_name       ON role_permissions (role_name);
CREATE INDEX IF NOT EXISTS idx_rp_permission_code ON role_permissions (permission_code);


CREATE TABLE IF NOT EXISTS abac_policies (
    id            VARCHAR(36)  PRIMARY KEY,
    policy_id     VARCHAR(64)  NOT NULL UNIQUE,
    name          VARCHAR(128) NOT NULL,
    description   VARCHAR(255),
    effect        VARCHAR(16)  NOT NULL DEFAULT 'ALLOW',
    action        VARCHAR(64)  NOT NULL,
    resource_type VARCHAR(64)  NOT NULL,
    conditions    JSONB,
    is_active     BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_abac_policy_id ON abac_policies (policy_id);

-- ---------------------------------------------------------------------------
-- 2. Cases & Assignments
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS cases (
    id               VARCHAR(36)  PRIMARY KEY,
    case_number      VARCHAR(64)  NOT NULL UNIQUE,
    title            VARCHAR(255) NOT NULL,
    case_type        VARCHAR(64)  NOT NULL,
    description      TEXT,
    status           VARCHAR(32)  NOT NULL DEFAULT 'Active',
    priority         VARCHAR(32)  NOT NULL DEFAULT 'Medium',
    sensitivity      VARCHAR(32)  NOT NULL DEFAULT 'Confidential',
    created_by       VARCHAR(36)  REFERENCES users(id),
    assigned_officer VARCHAR(255),
    department       VARCHAR(128) NOT NULL,
    created_at       TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at       TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    closed_at        TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_cases_case_number ON cases (case_number);
CREATE INDEX IF NOT EXISTS idx_cases_status      ON cases (status);

DROP TRIGGER IF EXISTS trg_cases_updated_at ON cases;
CREATE TRIGGER trg_cases_updated_at
    BEFORE UPDATE ON cases
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();


CREATE TABLE IF NOT EXISTS case_assignments (
    id           VARCHAR(36) PRIMARY KEY,
    case_id      VARCHAR(36) NOT NULL REFERENCES cases(id)  ON DELETE CASCADE,
    user_id      VARCHAR(36) NOT NULL REFERENCES users(id)  ON DELETE CASCADE,
    role_in_case VARCHAR(64) NOT NULL DEFAULT 'Lead Investigator',
    assigned_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_case_assignments_case_id ON case_assignments (case_id);
CREATE INDEX IF NOT EXISTS idx_case_assignments_user_id ON case_assignments (user_id);

-- ---------------------------------------------------------------------------
-- 3. Documents & Versions
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS documents (
    id                 VARCHAR(36) PRIMARY KEY,
    case_id            VARCHAR(36) NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    document_type      VARCHAR(64) NOT NULL,
    title              VARCHAR(255) NOT NULL,
    description        TEXT,
    classification     VARCHAR(32) NOT NULL DEFAULT 'Confidential',
    current_version_id VARCHAR(36),
    owner_id           VARCHAR(36) REFERENCES users(id),
    status             VARCHAR(32) NOT NULL DEFAULT 'Active',
    created_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at         TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_documents_case_id ON documents (case_id);
CREATE INDEX IF NOT EXISTS idx_documents_type    ON documents (document_type);

DROP TRIGGER IF EXISTS trg_documents_updated_at ON documents;
CREATE TRIGGER trg_documents_updated_at
    BEFORE UPDATE ON documents
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();


CREATE TABLE IF NOT EXISTS document_versions (
    id              VARCHAR(36)  PRIMARY KEY,
    document_id     VARCHAR(36)  NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    version_number  INTEGER      NOT NULL DEFAULT 1,
    storage_key     VARCHAR(512) NOT NULL,
    sha256_hash     VARCHAR(64)  NOT NULL,
    file_name       VARCHAR(255) NOT NULL,
    file_size       INTEGER      NOT NULL DEFAULT 0,
    mime_type       VARCHAR(128) NOT NULL DEFAULT 'application/pdf',
    created_by      VARCHAR(36)  REFERENCES users(id),
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    change_reason   VARCHAR(255) DEFAULT 'Initial upload',
    status          VARCHAR(32)  NOT NULL DEFAULT 'ACTIVE'
);

CREATE INDEX IF NOT EXISTS idx_doc_versions_document_id ON document_versions (document_id);
CREATE INDEX IF NOT EXISTS idx_doc_versions_sha256      ON document_versions (sha256_hash);


CREATE TABLE IF NOT EXISTS storage_objects (
    id                   VARCHAR(36)  PRIMARY KEY,
    version_id           VARCHAR(36)  NOT NULL UNIQUE REFERENCES document_versions(id) ON DELETE CASCADE,
    storage_provider     VARCHAR(32)  NOT NULL DEFAULT 'minio',
    bucket               VARCHAR(128) NOT NULL,
    storage_key          VARCHAR(512) NOT NULL,
    canonical_bucket     VARCHAR(128),
    canonical_key        VARCHAR(512),
    etag                 VARCHAR(128),
    object_version_id    VARCHAR(256),
    mime_type            VARCHAR(128),
    file_size            INTEGER      NOT NULL,
    is_tampered_simulated BOOLEAN     NOT NULL DEFAULT FALSE
);

ALTER TABLE storage_objects ADD COLUMN IF NOT EXISTS canonical_bucket VARCHAR(128);
ALTER TABLE storage_objects ADD COLUMN IF NOT EXISTS canonical_key VARCHAR(512);
ALTER TABLE storage_objects ADD COLUMN IF NOT EXISTS etag VARCHAR(128);
ALTER TABLE storage_objects ADD COLUMN IF NOT EXISTS object_version_id VARCHAR(256);
ALTER TABLE storage_objects ADD COLUMN IF NOT EXISTS mime_type VARCHAR(128);

-- ---------------------------------------------------------------------------
-- 4. AI / OCR & Processing
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS ai_processing_jobs (
    id           VARCHAR(36) PRIMARY KEY,
    document_id  VARCHAR(36) NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    version_id   VARCHAR(36) NOT NULL,
    job_type     VARCHAR(32) NOT NULL DEFAULT 'FULL_PIPELINE',
    status       VARCHAR(32) NOT NULL DEFAULT 'QUEUED',
    progress     INTEGER     NOT NULL DEFAULT 0,
    error        TEXT,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    started_at   TIMESTAMPTZ,
    completed_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_ai_jobs_document_id ON ai_processing_jobs (document_id);


CREATE TABLE IF NOT EXISTS ai_extractions (
    id                        VARCHAR(36)       PRIMARY KEY,
    document_id               VARCHAR(36)       NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    version_id                VARCHAR(36)       NOT NULL,
    model_version             VARCHAR(64)       NOT NULL DEFAULT 'nyaya-nlp-v2.1',
    classification            VARCHAR(64)       NOT NULL,
    classification_confidence DOUBLE PRECISION  NOT NULL DEFAULT 0.95,
    extracted_fields          JSONB,
    raw_text                  TEXT,
    review_required           BOOLEAN           NOT NULL DEFAULT FALSE,
    created_at                TIMESTAMPTZ       NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ai_extractions_document_id ON ai_extractions (document_id);


CREATE TABLE IF NOT EXISTS ai_reviews (
    id                      VARCHAR(36) PRIMARY KEY,
    extraction_id           VARCHAR(36) NOT NULL REFERENCES ai_extractions(id) ON DELETE CASCADE,
    document_id             VARCHAR(36) NOT NULL,
    reviewer_id             VARCHAR(36) NOT NULL REFERENCES users(id),
    original_classification VARCHAR(64) NOT NULL,
    reviewed_classification VARCHAR(64) NOT NULL,
    original_fields         JSONB,
    reviewed_fields         JSONB,
    decision                VARCHAR(32) NOT NULL DEFAULT 'ACCEPTED',
    review_notes            TEXT,
    reviewed_at             TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ---------------------------------------------------------------------------
-- 5. Search Index
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS search_documents (
    id            VARCHAR(36)  PRIMARY KEY,
    document_id   VARCHAR(36)  NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    version_id    VARCHAR(36)  NOT NULL,
    case_id       VARCHAR(36)  NOT NULL,
    title         VARCHAR(255) NOT NULL,
    document_type VARCHAR(64)  NOT NULL,
    classification VARCHAR(32) NOT NULL,
    content_text  TEXT         NOT NULL,
    tags          VARCHAR(512),
    created_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_search_documents_document_id ON search_documents (document_id);
CREATE INDEX IF NOT EXISTS idx_search_documents_case_id     ON search_documents (case_id);

-- ---------------------------------------------------------------------------
-- 6. Evidence & Custody
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS evidence (
    id                VARCHAR(36)  PRIMARY KEY,
    case_id           VARCHAR(36)  NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    evidence_number   VARCHAR(64)  NOT NULL UNIQUE,
    type              VARCHAR(64)  NOT NULL,
    description       TEXT         NOT NULL,
    collected_by      VARCHAR(255) NOT NULL,
    collected_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    current_custodian VARCHAR(255) NOT NULL,
    status            VARCHAR(32)  NOT NULL DEFAULT 'COLLECTED',
    classification    VARCHAR(32)  NOT NULL DEFAULT 'Confidential',
    document_id       VARCHAR(36)  REFERENCES documents(id),
    created_at        TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at        TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_evidence_case_id         ON evidence (case_id);
CREATE INDEX IF NOT EXISTS idx_evidence_evidence_number ON evidence (evidence_number);

DROP TRIGGER IF EXISTS trg_evidence_updated_at ON evidence;
CREATE TRIGGER trg_evidence_updated_at
    BEFORE UPDATE ON evidence
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();


CREATE TABLE IF NOT EXISTS custody_events (
    id                  VARCHAR(36)  PRIMARY KEY,
    evidence_id         VARCHAR(36)  NOT NULL REFERENCES evidence(id) ON DELETE CASCADE,
    from_user           VARCHAR(255) NOT NULL,
    to_user             VARCHAR(255) NOT NULL,
    action              VARCHAR(64)  NOT NULL,
    timestamp           TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    context             TEXT,
    signature_reference VARCHAR(255),
    previous_event_hash VARCHAR(64)  NOT NULL,
    event_hash          VARCHAR(64)  NOT NULL UNIQUE
);

CREATE INDEX IF NOT EXISTS idx_custody_events_evidence_id ON custody_events (evidence_id);

-- ---------------------------------------------------------------------------
-- 7. Integrity & Blockchain
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS integrity_records (
    id                   VARCHAR(36) PRIMARY KEY,
    document_id          VARCHAR(36) NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    version_id           VARCHAR(36) NOT NULL,
    sha256_hash          VARCHAR(64) NOT NULL,
    verification_status  VARCHAR(32) NOT NULL DEFAULT 'VERIFIED',
    last_verified_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    is_tampered_simulated BOOLEAN    NOT NULL DEFAULT FALSE,
    tamper_notes         TEXT
);

CREATE INDEX IF NOT EXISTS idx_integrity_records_document_id ON integrity_records (document_id);
CREATE INDEX IF NOT EXISTS idx_integrity_records_sha256      ON integrity_records (sha256_hash);


CREATE TABLE IF NOT EXISTS blockchain_transactions (
    id              VARCHAR(36)  PRIMARY KEY,
    document_id     VARCHAR(36)  NOT NULL,
    version_id      VARCHAR(36)  NOT NULL,
    sha256          VARCHAR(64)  NOT NULL,
    transaction_id  VARCHAR(128) NOT NULL UNIQUE,
    block_reference VARCHAR(64)  NOT NULL,
    network         VARCHAR(64)  NOT NULL DEFAULT 'Hyperledger Fabric v2.5',
    channel         VARCHAR(64)  NOT NULL DEFAULT 'nyayachannel',
    status          VARCHAR(32)  NOT NULL DEFAULT 'COMMITTED',
    timestamp       TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_blockchain_document_id   ON blockchain_transactions (document_id);
CREATE INDEX IF NOT EXISTS idx_blockchain_transaction_id ON blockchain_transactions (transaction_id);

-- ---------------------------------------------------------------------------
-- 8. Digital Signatures
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS digital_signatures (
    id                  VARCHAR(36)  PRIMARY KEY,
    resource_type       VARCHAR(32)  NOT NULL,
    resource_id         VARCHAR(36)  NOT NULL,
    signer_id           VARCHAR(36)  NOT NULL REFERENCES users(id),
    signature_type      VARCHAR(32)  NOT NULL DEFAULT 'Aadhaar-eSign',
    signature_reference VARCHAR(255) NOT NULL,
    signed_hash         VARCHAR(64)  NOT NULL,
    signed_at           TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    status              VARCHAR(32)  NOT NULL DEFAULT 'VALID'
);

CREATE INDEX IF NOT EXISTS idx_digital_signatures_resource_id ON digital_signatures (resource_id);

-- ---------------------------------------------------------------------------
-- 9. Audit & Security Monitoring
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS audit_events (
    id                  VARCHAR(36) PRIMARY KEY,
    timestamp           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    actor_id            VARCHAR(36),
    actor_role          VARCHAR(64),
    action              VARCHAR(64) NOT NULL,
    resource_type       VARCHAR(32) NOT NULL,
    resource_id         VARCHAR(36),
    case_id             VARCHAR(36),
    result              VARCHAR(16) NOT NULL DEFAULT 'SUCCESS',
    severity            VARCHAR(16) NOT NULL DEFAULT 'INFO',
    ip_address          VARCHAR(64) DEFAULT '127.0.0.1',
    user_agent          VARCHAR(255),
    metadata_json       JSONB,
    previous_event_hash VARCHAR(64) NOT NULL,
    event_hash          VARCHAR(64) NOT NULL UNIQUE
);

CREATE INDEX IF NOT EXISTS idx_audit_events_timestamp ON audit_events (timestamp);
CREATE INDEX IF NOT EXISTS idx_audit_events_actor_id  ON audit_events (actor_id);
CREATE INDEX IF NOT EXISTS idx_audit_events_action    ON audit_events (action);
CREATE INDEX IF NOT EXISTS idx_audit_events_case_id   ON audit_events (case_id);


CREATE TABLE IF NOT EXISTS security_events (
    id          VARCHAR(36) PRIMARY KEY,
    user_id     VARCHAR(36),
    event_type  VARCHAR(64) NOT NULL,
    resource_id VARCHAR(36),
    case_id     VARCHAR(36),
    risk_score  INTEGER     NOT NULL DEFAULT 50,
    severity    VARCHAR(16) NOT NULL DEFAULT 'MEDIUM',
    description TEXT        NOT NULL,
    detected_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    status      VARCHAR(32) NOT NULL DEFAULT 'NEW'
);

CREATE INDEX IF NOT EXISTS idx_security_events_user_id     ON security_events (user_id);
CREATE INDEX IF NOT EXISTS idx_security_events_event_type  ON security_events (event_type);
CREATE INDEX IF NOT EXISTS idx_security_events_detected_at ON security_events (detected_at);


CREATE TABLE IF NOT EXISTS security_alerts (
    id          VARCHAR(36)  PRIMARY KEY,
    title       VARCHAR(255) NOT NULL,
    description TEXT         NOT NULL,
    severity    VARCHAR(16)  NOT NULL DEFAULT 'HIGH',
    status      VARCHAR(32)  NOT NULL DEFAULT 'ACTIVE',
    event_id    VARCHAR(36)  REFERENCES security_events(id),
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    resolved_at TIMESTAMPTZ,
    resolved_by VARCHAR(36)
);

-- ---------------------------------------------------------------------------
-- 10. Certificates, Notifications & System Settings
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS certificates (
    id                 VARCHAR(36)  PRIMARY KEY,
    certificate_number VARCHAR(64)  NOT NULL UNIQUE,
    case_id            VARCHAR(36)  NOT NULL REFERENCES cases(id),
    document_id        VARCHAR(36)  REFERENCES documents(id),
    evidence_id        VARCHAR(36)  REFERENCES evidence(id),
    generated_by       VARCHAR(36)  NOT NULL REFERENCES users(id),
    file_storage_key   VARCHAR(512) NOT NULL,
    verification_hash  VARCHAR(64)  NOT NULL,
    created_at         TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_certificates_number ON certificates (certificate_number);


CREATE TABLE IF NOT EXISTS notifications (
    id            VARCHAR(36)  PRIMARY KEY,
    user_id       VARCHAR(36)  NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    type          VARCHAR(64)  NOT NULL,
    title         VARCHAR(255) NOT NULL,
    message       TEXT         NOT NULL,
    resource_type VARCHAR(32),
    resource_id   VARCHAR(36),
    is_read       BOOLEAN      NOT NULL DEFAULT FALSE,
    created_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_notifications_user_id ON notifications (user_id);


CREATE TABLE IF NOT EXISTS system_settings (
    id          VARCHAR(36)  PRIMARY KEY,
    key         VARCHAR(64)  NOT NULL UNIQUE,
    value       VARCHAR(255) NOT NULL,
    description VARCHAR(255),
    updated_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_system_settings_key ON system_settings (key);

DROP TRIGGER IF EXISTS trg_system_settings_updated_at ON system_settings;
CREATE TRIGGER trg_system_settings_updated_at
    BEFORE UPDATE ON system_settings
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- =============================================================================
-- Seed Data
-- =============================================================================

-- ---------------------------------------------------------------------------
-- Roles
-- ---------------------------------------------------------------------------
INSERT INTO roles (id, name, description) VALUES
    ('role_admin',    'Administrator',        'Full system access and user management'),
    ('role_io',       'Investigating Officer', 'Case investigation and document management'),
    ('role_forensic', 'Forensic Staff',        'Evidence collection and forensic analysis'),
    ('role_senior',   'Senior Officer',        'Supervisory access with audit visibility')
ON CONFLICT (name) DO NOTHING;

-- ---------------------------------------------------------------------------
-- Permissions
-- ---------------------------------------------------------------------------
INSERT INTO permissions (id, code, name, description) VALUES
    ('perm_manage_users',         'manage_users',         'Manage Users',          'Approve and manage user accounts'),
    ('perm_view',                 'view',                 'View',                  'View secured records'),
    ('perm_upload',               'upload',               'Upload',                'Upload secured records'),
    ('perm_download',             'download',             'Download',              'Download secured records'),
    ('perm_verify',               'verify',               'Verify',                'Verify record integrity'),
    ('perm_transfer',             'transfer',             'Transfer',              'Transfer evidence custody'),
    ('perm_sign',                 'sign',                 'Sign',                  'Digitally sign records'),
    ('perm_generate_certificate', 'generate_certificate', 'Generate Certificate',  'Generate integrity certificates'),
    ('perm_manage_access',        'manage_access',        'Manage Access',         'Manage ABAC/RBAC access policies'),
    ('perm_view_security_events', 'view_security_events', 'View Security Events',  'View security monitoring events'),
    ('perm_view_audit_logs',      'view_audit_logs',      'View Audit Logs',       'View tamper-evident audit chain'),
    ('perm_edit',                 'edit',                 'Edit',                  'Edit existing records'),
    ('perm_delete',               'delete',               'Delete',                'Delete records')
ON CONFLICT (code) DO NOTHING;

-- ---------------------------------------------------------------------------
-- Role → Permission Mappings
-- ---------------------------------------------------------------------------
INSERT INTO role_permissions (id, role_name, permission_code)
SELECT
    'rp_' || md5(v.role_name || ':' || v.permission_code),
    v.role_name,
    v.permission_code
FROM (VALUES
    -- Administrator: full access
    ('Administrator', 'manage_users'),
    ('Administrator', 'view'),
    ('Administrator', 'upload'),
    ('Administrator', 'download'),
    ('Administrator', 'verify'),
    ('Administrator', 'transfer'),
    ('Administrator', 'sign'),
    ('Administrator', 'generate_certificate'),
    ('Administrator', 'manage_access'),
    ('Administrator', 'view_security_events'),
    ('Administrator', 'view_audit_logs'),
    ('Administrator', 'edit'),
    ('Administrator', 'delete'),
    -- Investigating Officer
    ('Investigating Officer', 'view'),
    ('Investigating Officer', 'upload'),
    ('Investigating Officer', 'download'),
    ('Investigating Officer', 'verify'),
    ('Investigating Officer', 'transfer'),
    ('Investigating Officer', 'sign'),
    ('Investigating Officer', 'generate_certificate'),
    -- Forensic Staff
    ('Forensic Staff', 'view'),
    ('Forensic Staff', 'upload'),
    ('Forensic Staff', 'download'),
    ('Forensic Staff', 'verify'),
    ('Forensic Staff', 'sign'),
    ('Forensic Staff', 'generate_certificate'),
    -- Senior Officer
    ('Senior Officer', 'view'),
    ('Senior Officer', 'upload'),
    ('Senior Officer', 'download'),
    ('Senior Officer', 'verify'),
    ('Senior Officer', 'transfer'),
    ('Senior Officer', 'sign'),
    ('Senior Officer', 'generate_certificate'),
    ('Senior Officer', 'view_security_events'),
    ('Senior Officer', 'view_audit_logs')
) AS v(role_name, permission_code)
WHERE NOT EXISTS (
    SELECT 1 FROM role_permissions existing
    WHERE existing.role_name       = v.role_name
      AND existing.permission_code = v.permission_code
);

-- ---------------------------------------------------------------------------
-- Default Administrator Account
-- Password: NyayaVault@2026  (bcrypt via pgcrypto)
-- The FastAPI backend uses passlib[bcrypt] which is compatible with the
-- $2a$ / $2b$ bcrypt format produced by crypt(..., gen_salt('bf')).
-- ---------------------------------------------------------------------------
INSERT INTO users (
    id, email, full_name, employee_id, department, designation,
    role, clearance_level, is_active, password_hash
) VALUES (
    'usr_admin_001',
    'admin@nyayavault.gov.in',
    'Rajesh Kumar (IPS)',
    'DL-NCRB-2024-001',
    'National Crime Records Bureau',
    'Director & Chief Administrator',
    'Administrator',
    'Level 4',
    TRUE,
    crypt('NyayaVault@2026', gen_salt('bf'))
)
ON CONFLICT (email) DO UPDATE SET
    role            = EXCLUDED.role,
    clearance_level = EXCLUDED.clearance_level,
    is_active       = TRUE,
    updated_at      = NOW();

-- =============================================================================
-- END OF BOOTSTRAP SCRIPT
-- =============================================================================
-- After running this script:
--   1. Optionally run `python seed.py` from the backend directory to add demo
--      users and sample case data. The FastAPI backend does not seed on startup.
--   2. Verify connectivity at GET /api/v1/health/db
--   3. Login at POST /api/v1/auth/login with the admin credentials above.
-- =============================================================================
