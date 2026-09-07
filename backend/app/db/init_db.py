import logging
import json
from datetime import datetime, timedelta, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.base import Base
from app.db.session import engine
from app.db.models import (
    User,
    RegistrationRequest,
    Role,
    Permission,
    RolePermission,
    ABACPolicy,
    Case,
    Document,
    DocumentVersion,
    StorageObject,
    Evidence,
    CustodyEvent,
    IntegrityRecord,
    BlockchainTransaction,
    AuditEvent,
    SecurityEvent,
    SecurityAlert,
    Notification,
    SystemSetting,
)
from app.core.security.hashing import get_password_hash, compute_sha256
from app.core.security.rbac import RoleEnum, PermissionEnum, ROLE_PERMISSIONS_MAP
from app.config.settings import settings as app_settings

logger = logging.getLogger("nyayavault.init_db")

DEMO_SEED_MARKER = "nyayavault_demo_seed_version"
DEMO_SEED_VERSION = "2026.1"
DEMO_REFERENCE_TIME = datetime(2026, 9, 6, 9, 0, tzinfo=timezone.utc)


async def init_db_schema():
    """Initializes schema tables for PostgreSQL database"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)



async def seed_demo_dataset(db: AsyncSession):
    """Seed a deterministic, metadata-only fictional dataset once per database."""
    marker_result = await db.execute(select(SystemSetting).filter_by(key=DEMO_SEED_MARKER))
    marker = marker_result.scalars().first()
    if marker and marker.value == DEMO_SEED_VERSION:
        logger.info("Demo dataset version %s is already present.", DEMO_SEED_VERSION)
        return

    demo_cases = [
        ("demo_case_001", "NV-DEMO-2026-001", "Operation Monsoon Ledger", "Cyber Financial Review", "Active", "High", 82),
        ("demo_case_002", "NV-DEMO-2026-002", "Project Saffron Signal", "Digital Evidence Review", "Under Review", "Medium", 68),
        ("demo_case_003", "NV-DEMO-2026-003", "Harbor Transit Records", "Commercial Documentation", "Pending", "High", 55),
        ("demo_case_004", "NV-DEMO-2026-004", "Blue Neem Archive", "Forensic Records", "Closed", "Low", 44),
        ("demo_case_005", "NV-DEMO-2026-005", "Cobalt Parcel Inquiry", "Evidence Verification", "Active", "Urgent", 31),
        ("demo_case_006", "NV-DEMO-2026-006", "Amber Registry Review", "Court Records", "Under Review", "Medium", 18),
    ]
    for case_id, case_number, title, case_type, status, priority, days_ago in demo_cases:
        if not await db.get(Case, case_id):
            created_at = DEMO_REFERENCE_TIME - timedelta(days=days_ago)
            db.add(Case(
                id=case_id,
                case_number=case_number,
                title=title,
                case_type=case_type,
                description="Fictional NyayaVault demonstration investigation record.",
                status=status,
                priority=priority,
                sensitivity="Confidential",
                created_by="usr_io_001",
                assigned_officer="Demo Investigation Officer",
                department="NyayaVault Demonstration Unit",
                created_at=created_at,
                updated_at=created_at + timedelta(days=1),
                closed_at=created_at + timedelta(days=12) if status == "Closed" else None,
            ))
    await db.flush()

    document_specs = [
        ("demo_doc_001", "demo_ver_001", "demo_sto_001", "demo_case_001", "FIR", "Monsoon Ledger Initial Report", "Active", "VERIFIED", 82),
        ("demo_doc_002", "demo_ver_002", "demo_sto_002", "demo_case_001", "Police Report", "Monsoon Ledger Field Notes", "Active", "VERIFIED", 67),
        ("demo_doc_003", "demo_ver_003", "demo_sto_003", "demo_case_002", "Evidence Report", "Saffron Signal Media Register", "Active", "VERIFIED", 54),
        ("demo_doc_004", "demo_ver_004", "demo_sto_004", "demo_case_002", "Forensic Report", "Saffron Signal Device Examination", "Review Required", "PENDING", 42),
        ("demo_doc_005", "demo_ver_005", "demo_sto_005", "demo_case_003", "Charge Sheet", "Harbor Transit Draft Charge Sheet", "Active", "VERIFIED", 35),
        ("demo_doc_006", "demo_ver_006", "demo_sto_006", "demo_case_003", "Court Document", "Harbor Transit Listing Notice", "Active", "VERIFIED", 29),
        ("demo_doc_007", "demo_ver_007", "demo_sto_007", "demo_case_004", "FIR", "Blue Neem Archive Registration", "Archived", "VERIFIED", 24),
        ("demo_doc_008", "demo_ver_008", "demo_sto_008", "demo_case_004", "Forensic Report", "Blue Neem Archive Validation", "Active", "PENDING", 20),
        ("demo_doc_009", "demo_ver_009", "demo_sto_009", "demo_case_005", "Evidence Report", "Cobalt Parcel Evidence Inventory", "Active", "VERIFIED", 16),
        ("demo_doc_010", "demo_ver_010", "demo_sto_010", "demo_case_005", "Police Report", "Cobalt Parcel Transfer Memo", "Active", "VERIFIED", 12),
        ("demo_doc_011", "demo_ver_011", "demo_sto_011", "demo_case_006", "Court Document", "Amber Registry Hearing Record", "Active", "VERIFIED", 9),
        ("demo_doc_012", "demo_ver_012", "demo_sto_012", "demo_case_006", "Charge Sheet", "Amber Registry Review Summary", "Review Required", "PENDING", 6),
        ("demo_doc_013", "demo_ver_013", "demo_sto_013", "demo_case_001", "Evidence Report", "Monsoon Ledger Chain Summary", "Active", "VERIFIED", 3),
        ("demo_doc_014", "demo_ver_014", "demo_sto_014", "demo_case_005", "Forensic Report", "Cobalt Parcel Laboratory Note", "Active", "VERIFIED", 1),
    ]
    for doc_id, version_id, storage_id, case_id, document_type, title, status, integrity_status, days_ago in document_specs:
        created_at = DEMO_REFERENCE_TIME - timedelta(days=days_ago)
        storage_key = f"demo/{case_id}/documents/{doc_id}/{version_id}.pdf"
        file_name = f"{doc_id}.pdf"
        file_size = 2048 + days_ago
        sha256_hash = compute_sha256(f"NYAYAVAULT-DEMO:{doc_id}:{version_id}".encode())

        if not await db.get(Document, doc_id):
            db.add(Document(
                id=doc_id,
                case_id=case_id,
                document_type=document_type,
                title=title,
                description="Fictional NyayaVault demonstration document metadata.",
                classification="Confidential",
                current_version_id=version_id,
                owner_id="usr_io_001",
                status=status,
                created_at=created_at,
                updated_at=created_at,
            ))
        if not await db.get(DocumentVersion, version_id):
            db.add(DocumentVersion(
                id=version_id,
                document_id=doc_id,
                version_number=1,
                storage_key=storage_key,
                sha256_hash=sha256_hash,
                file_name=file_name,
                file_size=file_size,
                mime_type="application/pdf",
                created_by="usr_io_001",
                created_at=created_at,
                change_reason="Deterministic demonstration seed",
                status="ACTIVE",
            ))
        if not await db.get(StorageObject, storage_id):
            db.add(StorageObject(
                id=storage_id,
                version_id=version_id,
                storage_provider=app_settings.STORAGE_PROVIDER,
                bucket=app_settings.STORAGE_BUCKET,
                storage_key=storage_key,
                file_size=file_size,
                is_tampered_simulated=False,
            ))
        integrity_id = f"demo_int_{doc_id[-3:]}"
        if not await db.get(IntegrityRecord, integrity_id):
            db.add(IntegrityRecord(
                id=integrity_id,
                document_id=doc_id,
                version_id=version_id,
                sha256_hash=sha256_hash,
                verification_status=integrity_status,
                last_verified_at=created_at + timedelta(hours=2),
                is_tampered_simulated=False,
                tamper_notes=None,
            ))
    await db.flush()

    evidence_specs = [
        ("demo_ev_001", "NV-DEMO-EV-001", "demo_case_001", "demo_doc_001", "Digital Evidence", "SECURED", 66),
        ("demo_ev_002", "NV-DEMO-EV-002", "demo_case_002", "demo_doc_004", "Physical", "IN_TRANSIT", 40),
        ("demo_ev_003", "NV-DEMO-EV-003", "demo_case_003", "demo_doc_005", "Document", "COURT_SUBMITTED", 28),
        ("demo_ev_004", "NV-DEMO-EV-004", "demo_case_005", "demo_doc_009", "Digital Evidence", "COLLECTED", 15),
        ("demo_ev_005", "NV-DEMO-EV-005", "demo_case_006", "demo_doc_011", "Biological", "SECURED", 5),
    ]
    for evidence_id, evidence_number, case_id, document_id, evidence_type, status, days_ago in evidence_specs:
        if not await db.get(Evidence, evidence_id):
            collected_at = DEMO_REFERENCE_TIME - timedelta(days=days_ago)
            db.add(Evidence(
                id=evidence_id,
                case_id=case_id,
                evidence_number=evidence_number,
                type=evidence_type,
                description="Fictional NyayaVault demonstration evidence record.",
                collected_by="Demo Collection Officer",
                collected_at=collected_at,
                current_custodian="Demo Evidence Custodian",
                status=status,
                classification="Confidential",
                document_id=document_id,
                created_at=collected_at,
                updated_at=collected_at,
            ))
    await db.flush()

    custody_specs = [
        ("demo_ev_001", "Collection", "Demo Collection Officer", "Demo Evidence Custodian", 65),
        ("demo_ev_001", "Transfer", "Demo Evidence Custodian", "Demo Forensic Desk", 62),
        ("demo_ev_002", "Collection", "Demo Collection Officer", "Demo Evidence Custodian", 39),
        ("demo_ev_002", "Transfer", "Demo Evidence Custodian", "Demo Transit Officer", 34),
        ("demo_ev_003", "Collection", "Demo Collection Officer", "Demo Records Custodian", 27),
        ("demo_ev_003", "Release", "Demo Records Custodian", "Demo Court Registry", 21),
        ("demo_ev_004", "Collection", "Demo Collection Officer", "Demo Evidence Custodian", 14),
        ("demo_ev_004", "Verify", "Demo Evidence Custodian", "Demo Forensic Desk", 8),
        ("demo_ev_005", "Collection", "Demo Collection Officer", "Demo Evidence Custodian", 4),
        ("demo_ev_005", "Transfer", "Demo Evidence Custodian", "Demo Laboratory Desk", 2),
    ]
    custody_previous_hashes = {}
    for index, (evidence_id, action, from_user, to_user, days_ago) in enumerate(custody_specs, start=1):
        previous_hash = custody_previous_hashes.get(evidence_id, compute_sha256(f"DEMO_CUSTODY_GENESIS:{evidence_id}".encode()))
        timestamp = DEMO_REFERENCE_TIME - timedelta(days=days_ago)
        event_hash = compute_sha256(f"{evidence_id}:{action}:{timestamp.isoformat()}:{previous_hash}".encode())
        custody_previous_hashes[evidence_id] = event_hash
        custody_id = f"demo_custody_{index:03d}"
        if not await db.get(CustodyEvent, custody_id):
            db.add(CustodyEvent(
                id=custody_id,
                evidence_id=evidence_id,
                from_user=from_user,
                to_user=to_user,
                action=action,
                timestamp=timestamp,
                context="Fictional NyayaVault demonstration custody activity.",
                signature_reference=f"DEMO-CUSTODY-SIG-{index:03d}",
                previous_event_hash=previous_hash,
                event_hash=event_hash,
            ))
    await db.flush()

    audit_specs = [
        ("DOCUMENT_UPLOAD", "document", "demo_doc_001", "demo_case_001", "SUCCESS", "INFO", 80),
        ("SEARCH", "search", None, None, "SUCCESS", "INFO", 64),
        ("DOCUMENT_VIEW", "document", "demo_doc_004", "demo_case_002", "SUCCESS", "INFO", 49),
        ("INTEGRITY_VERIFY", "document", "demo_doc_005", "demo_case_003", "SUCCESS", "INFO", 38),
        ("DOCUMENT_DOWNLOAD", "document", "demo_doc_006", "demo_case_003", "SUCCESS", "INFO", 27),
        ("EVIDENCE_TRANSFER", "evidence", "demo_ev_002", "demo_case_002", "SUCCESS", "INFO", 19),
        ("CERTIFICATE_GENERATE", "certificate", None, "demo_case_003", "SUCCESS", "INFO", 13),
        ("ACCESS_DENIED", "document", "demo_doc_012", "demo_case_006", "DENIED", "WARNING", 8),
        ("DOCUMENT_UPLOAD", "document", "demo_doc_013", "demo_case_001", "SUCCESS", "INFO", 5),
        ("SEARCH", "search", None, None, "SUCCESS", "INFO", 3),
        ("INTEGRITY_VERIFY", "document", "demo_doc_014", "demo_case_005", "SUCCESS", "INFO", 1),
        ("ACCESS_DENIED", "evidence", "demo_ev_004", "demo_case_005", "DENIED", "WARNING", 0),
    ]
    latest_audit_result = await db.execute(select(AuditEvent).order_by(AuditEvent.timestamp.desc()).limit(1))
    latest_audit = latest_audit_result.scalars().first()
    audit_timestamps = [DEMO_REFERENCE_TIME - timedelta(days=days_ago) for *_, days_ago in audit_specs]
    if latest_audit:
        latest_timestamp = latest_audit.timestamp
        if latest_timestamp.tzinfo is None:
            latest_timestamp = latest_timestamp.replace(tzinfo=timezone.utc)
        if latest_timestamp >= audit_timestamps[0]:
            audit_timestamps = [latest_timestamp + timedelta(minutes=5 * (index + 1)) for index in range(len(audit_specs))]
    previous_audit_hash = latest_audit.event_hash if latest_audit else compute_sha256(b"GENESIS_AUDIT_BLOCK_NYAYAVAULT_2026")
    for index, ((action, resource_type, resource_id, case_id, result, severity, _), timestamp) in enumerate(zip(audit_specs, audit_timestamps), start=1):
        audit_id = f"demo_audit_{index:03d}"
        metadata = {"source": "deterministic-demo-seed"}
        metadata_json = json.dumps(metadata, sort_keys=True)
        event_hash = compute_sha256(f"usr_io_001:Investigating Officer:{action}:{resource_type}:{resource_id}:{result}:{severity}:{previous_audit_hash}:{metadata_json}".encode())
        if not await db.get(AuditEvent, audit_id):
            db.add(AuditEvent(
                id=audit_id,
                timestamp=timestamp,
                actor_id="usr_io_001",
                actor_role="Investigating Officer",
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                case_id=case_id,
                result=result,
                severity=severity,
                ip_address="127.0.0.1",
                user_agent="NyayaVault-Demo",
                metadata_json=metadata,
                previous_event_hash=previous_audit_hash,
                event_hash=event_hash,
            ))
        previous_audit_hash = event_hash
    await db.flush()

    security_specs = [
        ("demo_security_001", "FAILED_LOGIN", "LOW", "RESOLVED", 22, 60),
        ("demo_security_002", "ACCESS_DENIED", "MEDIUM", "INVESTIGATING", 47, 14),
        ("demo_security_003", "ABNORMAL_DOWNLOAD", "HIGH", "NEW", 76, 9),
        ("demo_security_004", "INTEGRITY_MISMATCH", "HIGH", "RESOLVED", 81, 6),
        ("demo_security_005", "ACCESS_DENIED", "CRITICAL", "NEW", 92, 3),
        ("demo_security_006", "FAILED_LOGIN", "MEDIUM", "NEW", 55, 1),
    ]
    for security_id, event_type, severity, status, risk_score, days_ago in security_specs:
        if not await db.get(SecurityEvent, security_id):
            db.add(SecurityEvent(
                id=security_id,
                user_id="usr_io_001",
                event_type=event_type,
                resource_id=None,
                case_id=None,
                risk_score=risk_score,
                severity=severity,
                description="Fictional NyayaVault demonstration security event.",
                detected_at=DEMO_REFERENCE_TIME - timedelta(days=days_ago),
                status=status,
            ))

    if marker:
        marker.value = DEMO_SEED_VERSION
        marker.description = "Version marker for the deterministic fictional demo dataset"
    else:
        db.add(SystemSetting(
            key=DEMO_SEED_MARKER,
            value=DEMO_SEED_VERSION,
            description="Version marker for the deterministic fictional demo dataset",
        ))
    await db.commit()
    logger.info("Seeded deterministic fictional demo dataset version %s.", DEMO_SEED_VERSION)


async def seed_db(db: AsyncSession):
    # Check if already seeded
    existing_user = await db.execute(select(User).filter_by(email="admin@nyayavault.gov.in"))
    if existing_user.scalars().first():
        logger.info("Database already seeded.")
        await seed_demo_dataset(db)
        return

    logger.info("Seeding database with initial roles, users, permissions, and sample cases...")

    # 1. Seed Permissions
    permissions = [
        Permission(code=p.value, name=p.name.replace("_", " ").title(), description=f"Permission to {p.value}")
        for p in PermissionEnum
    ]
    db.add_all(permissions)
    await db.flush()

    # 2. Seed Roles and RolePermissions
    for role_name, perms in ROLE_PERMISSIONS_MAP.items():
        role = Role(name=role_name, description=f"System role for {role_name}")
        db.add(role)
        for perm_code in perms:
            rp = RolePermission(role_name=role_name, permission_code=perm_code)
            db.add(rp)
    await db.flush()

    # 3. Seed Users
    default_pw = get_password_hash("NyayaVault@2026")

    users = [
        User(
            id="usr_admin_001",
            email="admin@nyayavault.gov.in",
            full_name="Rajesh Kumar (IPS)",
            employee_id="DL-NCRB-2024-001",
            department="National Crime Records Bureau",
            designation="Director & Chief Administrator",
            role=RoleEnum.ADMINISTRATOR.value,
            clearance_level="Level 4",
            is_active=True,
            password_hash=default_pw,
        ),
        User(
            id="usr_io_001",
            email="investigator@nyayavault.gov.in",
            full_name="Inspector Vikram Shinde",
            employee_id="MH-CID-10842",
            department="Crime Investigation Department",
            designation="Senior Investigating Officer",
            role=RoleEnum.INVESTIGATING_OFFICER.value,
            clearance_level="Level 3",
            is_active=True,
            password_hash=default_pw,
        ),
        User(
            id="usr_forensic_001",
            email="forensics@nyayavault.gov.in",
            full_name="Dr. Ananya Roy",
            employee_id="CFSL-DEL-3381",
            department="Central Forensic Science Laboratory",
            designation="Senior Forensic Examiner",
            role=RoleEnum.FORENSIC_STAFF.value,
            clearance_level="Level 3",
            is_active=True,
            password_hash=default_pw,
        ),
        User(
            id="usr_senior_001",
            email="senior@nyayavault.gov.in",
            full_name="Kavita Deshmukh (SPS)",
            employee_id="MH-POL-0042",
            department="State Police Headquarters",
            designation="Superintendent of Police",
            role=RoleEnum.SENIOR_OFFICER.value,
            clearance_level="Level 4",
            is_active=True,
            password_hash=default_pw,
        ),
    ]
    db.add_all(users)
    await db.flush()

    # 4. Seed ABAC Policies
    policies = [
        ABACPolicy(
            policy_id="POL-CLEARANCE-001",
            name="Clearance Level Policy",
            description="Restricts Top Secret records to Level 4 clearance personnel",
            effect="ALLOW",
            action="view",
            resource_type="document",
            conditions={"min_clearance": "Level 4", "classification": "Top Secret"},
            is_active=True,
        ),
        ABACPolicy(
            policy_id="POL-FORENSIC-001",
            name="Forensic Evidence Verification Policy",
            description="Permits Forensic Staff to verify and transfer digital/biological evidence",
            effect="ALLOW",
            action="verify",
            resource_type="evidence",
            conditions={"allowed_roles": ["Forensic Staff", "Administrator"]},
            is_active=True,
        ),
    ]
    db.add_all(policies)

    # 5. Seed Sample Case
    sample_case = Case(
        id="case_mh_01428",
        case_number="MH-PN-2026-01428",
        title="State of Maharashtra vs. Sandeep Nair & Others (Cyber Financial Fraud)",
        case_type="Cyber Financial Fraud",
        description="Investigation into automated multi-tier hawala transactions and falsified digital invoicing.",
        status="Active",
        priority="High",
        sensitivity="Confidential",
        created_by="usr_io_001",
        assigned_officer="Inspector Vikram Shinde",
        department="Crime Investigation Department",
    )
    db.add(sample_case)
    await db.flush()

    # 6. Seed Sample Document & Version
    sample_content = b"STATE OF MAHARASHTRA - FIRST INFORMATION REPORT (FIR 01428/2026)\nSections: IPC 420, 467, 468; IT Act 66D\nComplainant: Axis Bank Vigilance Wing\nSuspect: Sandeep Nair\nStatus: Registered"
    sample_hash = compute_sha256(sample_content)

    sample_doc = Document(
        id="doc_fir_001",
        case_id="case_mh_01428",
        document_type="FIR",
        title="FIR_01428_CyberFraud.pdf",
        description="Original registered FIR copy with digital timestamps",
        classification="Confidential",
        current_version_id="ver_001",
        owner_id="usr_io_001",
        status="Active",
    )
    db.add(sample_doc)
    await db.flush()

    doc_version = DocumentVersion(
        id="ver_001",
        document_id="doc_fir_001",
        version_number=1,
        storage_key="cases/case_mh_01428/documents/doc_fir_001/versions/ver_001/FIR_01428_CyberFraud.pdf",
        sha256_hash=sample_hash,
        file_name="FIR_01428_CyberFraud.pdf",
        file_size=len(sample_content),
        mime_type="application/pdf",
        created_by="usr_io_001",
        change_reason="Initial FIR Registration",
        status="ACTIVE",
    )
    db.add(doc_version)

    storage_obj = StorageObject(
        id="sto_001",
        version_id="ver_001",
        storage_provider=app_settings.STORAGE_PROVIDER,
        bucket=app_settings.STORAGE_BUCKET,
        storage_key="cases/case_mh_01428/documents/doc_fir_001/versions/ver_001/FIR_01428_CyberFraud.pdf",
        file_size=len(sample_content),
        is_tampered_simulated=False,
    )
    db.add(storage_obj)

    # 7. Seed Integrity & Blockchain records
    integrity_rec = IntegrityRecord(
        id="int_001",
        document_id="doc_fir_001",
        version_id="ver_001",
        sha256_hash=sample_hash,
        verification_status="VERIFIED",
        is_tampered_simulated=False,
    )
    db.add(integrity_rec)

    bc_tx = BlockchainTransaction(
        id="tx_bc_001",
        document_id="doc_fir_001",
        version_id="ver_001",
        sha256=sample_hash,
        transaction_id="0x7f4a8b9c2d1e0f34a5b6c7d8e9f0123456789abcdef0123456789abcdef01234",
        block_reference="Block #41,209",
        network="Hyperledger Fabric v2.5",
        channel="nyayachannel",
        status="COMMITTED",
    )
    db.add(bc_tx)

    # 8. Seed Evidence & Chain of Custody
    ev_item = Evidence(
        id="ev_001",
        case_id="case_mh_01428",
        evidence_number="EV-2026-MH-0891",
        type="Digital Evidence",
        description="Seized encrypted NVMe SSD containing offshore transaction records",
        collected_by="Inspector Vikram Shinde",
        current_custodian="Dr. Ananya Roy",
        status="SECURED",
        classification="Confidential",
        document_id="doc_fir_001",
    )
    db.add(ev_item)
    await db.flush()

    initial_custody_hash = compute_sha256(b"GENESIS_CUSTODY_EVENT_EV_001")
    event_1_hash = compute_sha256(f"COLLECTION:usr_io_001:usr_forensic_001:{initial_custody_hash}".encode())

    custody_ev1 = CustodyEvent(
        id="cust_001",
        evidence_id="ev_001",
        from_user="Inspector Vikram Shinde",
        to_user="Dr. Ananya Roy",
        action="Transfer",
        context="Handover from scene of crime to Central Forensic Science Lab for bit-stream disk imaging.",
        signature_reference="SIG-DSC-CID-99182",
        previous_event_hash=initial_custody_hash,
        event_hash=event_1_hash,
    )
    db.add(custody_ev1)

    # 9. Seed System Settings & Notifications
    settings = [
        SystemSetting(key="system_name", value="NyayaVault", description="Platform Name"),
        SystemSetting(key="section_65b_signatory", value="Rajesh Kumar (IPS)", description="Default Section 65B Signatory"),
        SystemSetting(key="tamper_alert_threshold", value="HIGH", description="Alert severity for hash mismatch"),
    ]
    db.add_all(settings)

    notif = Notification(
        user_id="usr_io_001",
        type="SYSTEM_WELCOME",
        title="Welcome to NyayaVault",
        message="System initialized successfully. All cryptographically secured modules are active.",
        resource_type="system",
        resource_id="sys_init",
    )
    db.add(notif)

    await db.commit()
    logger.info("Database initialized and seeded successfully.")
    await seed_demo_dataset(db)
