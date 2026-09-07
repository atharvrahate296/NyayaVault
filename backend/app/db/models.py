import uuid
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import (
    Column,
    String,
    Text,
    Integer,
    Float,
    Boolean,
    DateTime,
    ForeignKey,
    JSON,
    Enum as SQLEnum,
)
from sqlalchemy.orm import relationship
from app.db.base import Base


def utc_now():
    return datetime.now(timezone.utc)


def generate_uuid():
    return str(uuid.uuid4())


# ==========================================
# 1. Identity & RBAC
# ==========================================

class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    email = Column(String(255), unique=True, index=True, nullable=False)
    full_name = Column(String(255), nullable=False)
    employee_id = Column(String(64), unique=True, index=True, nullable=False)
    department = Column(String(128), nullable=False)
    designation = Column(String(128), nullable=False)
    role = Column(String(64), nullable=False, default="Investigating Officer")
    clearance_level = Column(String(32), nullable=False, default="Level 2")  # Level 1, Level 2, Level 3, Level 4
    is_active = Column(Boolean, default=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    last_login = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    # Relationships
    assignments = relationship("CaseAssignment", back_populates="user", cascade="all, delete-orphan")
    documents = relationship("Document", back_populates="owner")
    notifications = relationship("Notification", back_populates="user", cascade="all, delete-orphan")


class RegistrationRequest(Base):
    __tablename__ = "registration_requests"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    email = Column(String(255), unique=True, index=True, nullable=False)
    full_name = Column(String(255), nullable=False)
    employee_id = Column(String(64), unique=True, index=True, nullable=False)
    department = Column(String(128), nullable=False)
    designation = Column(String(128), nullable=False)
    posting_location = Column(String(255), nullable=False)
    justification = Column(Text, nullable=False)
    requested_role = Column(String(64), nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    supporting_document_name = Column(String(255), nullable=True)
    status = Column(String(16), default="PENDING", nullable=False, index=True)
    approved_by = Column(String(36), ForeignKey("users.id"), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    rejection_reason = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)


class Role(Base):
    __tablename__ = "roles"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(64), unique=True, index=True, nullable=False)
    description = Column(String(255), nullable=True)


class Permission(Base):
    __tablename__ = "permissions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    code = Column(String(64), unique=True, index=True, nullable=False)
    name = Column(String(128), nullable=False)
    description = Column(String(255), nullable=True)


class RolePermission(Base):
    __tablename__ = "role_permissions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    role_name = Column(String(64), nullable=False, index=True)
    permission_code = Column(String(64), nullable=False, index=True)


class ABACPolicy(Base):
    __tablename__ = "abac_policies"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    policy_id = Column(String(64), unique=True, index=True, nullable=False)
    name = Column(String(128), nullable=False)
    description = Column(String(255), nullable=True)
    effect = Column(String(16), default="ALLOW", nullable=False)  # ALLOW / DENY
    action = Column(String(64), nullable=False)  # view, upload, delete, etc.
    resource_type = Column(String(64), nullable=False)  # case, document, evidence
    conditions = Column(JSON, nullable=True)  # department, clearance, status criteria
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)


# ==========================================
# 2. Cases & Assignments
# ==========================================

class Case(Base):
    __tablename__ = "cases"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    case_number = Column(String(64), unique=True, index=True, nullable=False)
    title = Column(String(255), nullable=False)
    case_type = Column(String(64), nullable=False)  # Criminal, Cyber, Financial, Narcotics, etc.
    description = Column(Text, nullable=True)
    status = Column(String(32), default="Active", nullable=False, index=True)  # Active, Under Investigation, Pending Court, Closed
    priority = Column(String(32), default="Medium", nullable=False)  # Low, Medium, High, Urgent
    sensitivity = Column(String(32), default="Confidential", nullable=False)  # Public, Restricted, Confidential, Top Secret
    created_by = Column(String(36), ForeignKey("users.id"), nullable=True)
    assigned_officer = Column(String(255), nullable=True)
    department = Column(String(128), nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)
    closed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    documents = relationship("Document", back_populates="case", cascade="all, delete-orphan")
    evidence_items = relationship("Evidence", back_populates="case", cascade="all, delete-orphan")
    assignments = relationship("CaseAssignment", back_populates="case", cascade="all, delete-orphan")


class CaseAssignment(Base):
    __tablename__ = "case_assignments"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    case_id = Column(String(36), ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    role_in_case = Column(String(64), default="Lead Investigator", nullable=False)
    assigned_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    case = relationship("Case", back_populates="assignments")
    user = relationship("User", back_populates="assignments")


# ==========================================
# 3. Documents & Versions
# ==========================================

class Document(Base):
    __tablename__ = "documents"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    case_id = Column(String(36), ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True)
    document_type = Column(String(64), nullable=False, index=True)  # FIR, Police Report, Witness Statement, etc.
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    classification = Column(String(32), default="Confidential", nullable=False)
    current_version_id = Column(String(36), nullable=True)
    owner_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    status = Column(String(32), default="Active", nullable=False)  # Active, Archived, Review Required
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    # Relationships
    case = relationship("Case", back_populates="documents")
    owner = relationship("User", back_populates="documents")
    versions = relationship("DocumentVersion", back_populates="document", cascade="all, delete-orphan")
    ai_extractions = relationship("AIExtraction", back_populates="document", cascade="all, delete-orphan")
    integrity_records = relationship("IntegrityRecord", back_populates="document", cascade="all, delete-orphan")


class DocumentVersion(Base):
    __tablename__ = "document_versions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    document_id = Column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    version_number = Column(Integer, default=1, nullable=False)
    storage_key = Column(String(512), nullable=False)
    sha256_hash = Column(String(64), nullable=False, index=True)
    file_name = Column(String(255), nullable=False)
    file_size = Column(Integer, default=0, nullable=False)
    mime_type = Column(String(128), default="application/pdf", nullable=False)
    created_by = Column(String(36), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    change_reason = Column(String(255), default="Initial upload", nullable=True)
    status = Column(String(32), default="ACTIVE", nullable=False)

    document = relationship("Document", back_populates="versions")
    storage_object = relationship("StorageObject", back_populates="version", uselist=False, cascade="all, delete-orphan")


class StorageObject(Base):
    __tablename__ = "storage_objects"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    version_id = Column(String(36), ForeignKey("document_versions.id", ondelete="CASCADE"), nullable=False, unique=True)
    storage_provider = Column(String(32), default="minio", nullable=False)  # minio / s3
    bucket = Column(String(128), nullable=False)
    storage_key = Column(String(512), nullable=False)
    canonical_bucket = Column(String(128), nullable=True)
    canonical_key = Column(String(512), nullable=True)
    etag = Column(String(128), nullable=True)
    object_version_id = Column(String(256), nullable=True)
    mime_type = Column(String(128), nullable=True)
    file_size = Column(Integer, nullable=False)
    is_tampered_simulated = Column(Boolean, default=False, nullable=False)

    version = relationship("DocumentVersion", back_populates="storage_object")


# ==========================================
# 4. AI / OCR & Processing
# ==========================================

class AIProcessingJob(Base):
    __tablename__ = "ai_processing_jobs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    document_id = Column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    version_id = Column(String(36), nullable=False)
    job_type = Column(String(32), default="FULL_PIPELINE", nullable=False)  # OCR, CLASSIFICATION, EXTRACTION, FULL_PIPELINE
    status = Column(String(32), default="QUEUED", nullable=False)  # QUEUED, PROCESSING, COMPLETED, FAILED
    progress = Column(Integer, default=0, nullable=False)
    error = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)


class AIExtraction(Base):
    __tablename__ = "ai_extractions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    document_id = Column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    version_id = Column(String(36), nullable=False)
    model_version = Column(String(64), default="nyaya-nlp-v2.1", nullable=False)
    classification = Column(String(64), nullable=False)
    classification_confidence = Column(Float, default=0.95, nullable=False)
    extracted_fields = Column(JSON, nullable=True)
    raw_text = Column(Text, nullable=True)
    review_required = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    document = relationship("Document", back_populates="ai_extractions")


class AIReview(Base):
    __tablename__ = "ai_reviews"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    extraction_id = Column(String(36), ForeignKey("ai_extractions.id", ondelete="CASCADE"), nullable=False)
    document_id = Column(String(36), nullable=False)
    reviewer_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    original_classification = Column(String(64), nullable=False)
    reviewed_classification = Column(String(64), nullable=False)
    original_fields = Column(JSON, nullable=True)
    reviewed_fields = Column(JSON, nullable=True)
    decision = Column(String(32), default="ACCEPTED", nullable=False)  # ACCEPTED, MODIFIED, REJECTED
    review_notes = Column(Text, nullable=True)
    reviewed_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)


# ==========================================
# 5. Search Index
# ==========================================

class SearchDocument(Base):
    __tablename__ = "search_documents"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    document_id = Column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    version_id = Column(String(36), nullable=False)
    case_id = Column(String(36), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    document_type = Column(String(64), nullable=False)
    classification = Column(String(32), nullable=False)
    content_text = Column(Text, nullable=False)
    tags = Column(String(512), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)


# ==========================================
# 6. Evidence & Custody
# ==========================================

class Evidence(Base):
    __tablename__ = "evidence"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    case_id = Column(String(36), ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True)
    evidence_number = Column(String(64), unique=True, index=True, nullable=False)
    type = Column(String(64), nullable=False)  # Digital Evidence, Physical, Document, Biological, Ballistic
    description = Column(Text, nullable=False)
    collected_by = Column(String(255), nullable=False)
    collected_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    current_custodian = Column(String(255), nullable=False)
    status = Column(String(32), default="COLLECTED", nullable=False)  # COLLECTED, SECURED, IN_TRANSIT, COURT_SUBMITTED
    classification = Column(String(32), default="Confidential", nullable=False)
    document_id = Column(String(36), ForeignKey("documents.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    case = relationship("Case", back_populates="evidence_items")
    custody_events = relationship("CustodyEvent", back_populates="evidence", cascade="all, delete-orphan")


class CustodyEvent(Base):
    __tablename__ = "custody_events"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    evidence_id = Column(String(36), ForeignKey("evidence.id", ondelete="CASCADE"), nullable=False, index=True)
    from_user = Column(String(255), nullable=False)
    to_user = Column(String(255), nullable=False)
    action = Column(String(64), nullable=False)  # Collection, Transfer, Accept, Verify, Sign, Release, Receive
    timestamp = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    context = Column(Text, nullable=True)
    signature_reference = Column(String(255), nullable=True)
    previous_event_hash = Column(String(64), nullable=False)
    event_hash = Column(String(64), nullable=False, unique=True)

    evidence = relationship("Evidence", back_populates="custody_events")


# ==========================================
# 7. Integrity & Blockchain
# ==========================================

class IntegrityRecord(Base):
    __tablename__ = "integrity_records"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    document_id = Column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    version_id = Column(String(36), nullable=False)
    sha256_hash = Column(String(64), nullable=False, index=True)
    verification_status = Column(String(32), default="VERIFIED", nullable=False)  # VERIFIED, MISMATCH, PENDING
    last_verified_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    is_tampered_simulated = Column(Boolean, default=False, nullable=False)
    tamper_notes = Column(Text, nullable=True)

    document = relationship("Document", back_populates="integrity_records")


class BlockchainTransaction(Base):
    __tablename__ = "blockchain_transactions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    document_id = Column(String(36), nullable=False, index=True)
    version_id = Column(String(36), nullable=False)
    sha256 = Column(String(64), nullable=False)
    transaction_id = Column(String(128), unique=True, index=True, nullable=False)
    block_reference = Column(String(64), nullable=False)
    network = Column(String(64), default="Hyperledger Fabric v2.5", nullable=False)
    channel = Column(String(64), default="nyayachannel", nullable=False)
    status = Column(String(32), default="COMMITTED", nullable=False)
    timestamp = Column(DateTime(timezone=True), default=utc_now, nullable=False)


# ==========================================
# 8. Digital Signatures
# ==========================================

class DigitalSignature(Base):
    __tablename__ = "digital_signatures"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    resource_type = Column(String(32), nullable=False)  # document, evidence, custody_event
    resource_id = Column(String(36), nullable=False, index=True)
    signer_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    signature_type = Column(String(32), default="Aadhaar-eSign", nullable=False)  # DSC, Aadhaar-eSign, Internal-PKI
    signature_reference = Column(String(255), nullable=False)
    signed_hash = Column(String(64), nullable=False)
    signed_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    status = Column(String(32), default="VALID", nullable=False)


# ==========================================
# 9. Audit & Security Monitoring
# ==========================================

class AuditEvent(Base):
    __tablename__ = "audit_events"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    timestamp = Column(DateTime(timezone=True), default=utc_now, nullable=False, index=True)
    actor_id = Column(String(36), nullable=True, index=True)
    actor_role = Column(String(64), nullable=True)
    action = Column(String(64), nullable=False, index=True)
    resource_type = Column(String(32), nullable=False)
    resource_id = Column(String(36), nullable=True)
    case_id = Column(String(36), nullable=True, index=True)
    result = Column(String(16), default="SUCCESS", nullable=False)  # SUCCESS, FAILURE, DENIED
    severity = Column(String(16), default="INFO", nullable=False)  # INFO, WARNING, CRITICAL
    ip_address = Column(String(64), default="127.0.0.1", nullable=True)
    user_agent = Column(String(255), nullable=True)
    metadata_json = Column(JSON, nullable=True)
    previous_event_hash = Column(String(64), nullable=False)
    event_hash = Column(String(64), nullable=False, unique=True)


class SecurityEvent(Base):
    __tablename__ = "security_events"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), nullable=True, index=True)
    event_type = Column(String(64), nullable=False, index=True)  # FAILED_LOGIN, ACCESS_DENIED, INTEGRITY_MISMATCH, ABNORMAL_DOWNLOAD
    resource_id = Column(String(36), nullable=True)
    case_id = Column(String(36), nullable=True)
    risk_score = Column(Integer, default=50, nullable=False)  # 0 to 100
    severity = Column(String(16), default="MEDIUM", nullable=False)  # LOW, MEDIUM, HIGH, CRITICAL
    description = Column(Text, nullable=False)
    detected_at = Column(DateTime(timezone=True), default=utc_now, nullable=False, index=True)
    status = Column(String(32), default="NEW", nullable=False)  # NEW, INVESTIGATING, RESOLVED


class SecurityAlert(Base):
    __tablename__ = "security_alerts"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    severity = Column(String(16), default="HIGH", nullable=False)
    status = Column(String(32), default="ACTIVE", nullable=False)  # ACTIVE, RESOLVED, DISMISSED
    event_id = Column(String(36), ForeignKey("security_events.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    resolved_by = Column(String(36), nullable=True)


# ==========================================
# 10. Certificates, Notifications, Settings
# ==========================================

class Certificate(Base):
    __tablename__ = "certificates"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    certificate_number = Column(String(64), unique=True, index=True, nullable=False)
    case_id = Column(String(36), ForeignKey("cases.id"), nullable=False)
    document_id = Column(String(36), ForeignKey("documents.id"), nullable=True)
    evidence_id = Column(String(36), ForeignKey("evidence.id"), nullable=True)
    generated_by = Column(String(36), ForeignKey("users.id"), nullable=False)
    file_storage_key = Column(String(512), nullable=False)
    verification_hash = Column(String(64), nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    type = Column(String(64), nullable=False)  # INTEGRITY_ALERT, REVIEW_REQUIRED, TRANSFER_REQUEST, etc.
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    resource_type = Column(String(32), nullable=True)
    resource_id = Column(String(36), nullable=True)
    is_read = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    user = relationship("User", back_populates="notifications")


class SystemSetting(Base):
    __tablename__ = "system_settings"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    key = Column(String(64), unique=True, index=True, nullable=False)
    value = Column(String(255), nullable=False)
    description = Column(String(255), nullable=True)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)
