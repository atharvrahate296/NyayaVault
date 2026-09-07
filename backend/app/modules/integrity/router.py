import hashlib
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db, record_audit_log, require_permission
from app.core.exceptions.handlers import ResourceNotFoundException, IntegrityMismatchException
from app.db.models import (
    DocumentVersion,
    IntegrityRecord,
    BlockchainTransaction,
    SecurityEvent,
    SecurityAlert,
    User,
)
from app.modules.integrity.schemas import (
    IntegrityVerifyResponse,
    TamperSimulationResponse,
    RestoreResponse,
)
from app.modules.storage.service import storage_service

router = APIRouter(prefix="/integrity", tags=["Integrity Verification"])


@router.get("/{version_id}", response_model=IntegrityVerifyResponse)
async def get_integrity_status(
    version_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    int_res = await db.execute(select(IntegrityRecord).filter_by(version_id=version_id))
    int_rec = int_res.scalars().first()
    if not int_rec:
        raise ResourceNotFoundException("IntegrityRecord", version_id)

    bc_res = await db.execute(select(BlockchainTransaction).filter_by(version_id=version_id))
    bc_tx = bc_res.scalars().first()

    return IntegrityVerifyResponse(
        document_id=int_rec.document_id,
        version_id=int_rec.version_id,
        status=int_rec.verification_status,
        original_hash=int_rec.sha256_hash,
        calculated_hash=int_rec.sha256_hash,
        blockchain_tx_id=bc_tx.transaction_id if bc_tx else None,
        blockchain_block=bc_tx.block_reference if bc_tx else None,
        last_verified_at=int_rec.last_verified_at,
        is_tampered_simulated=int_rec.is_tampered_simulated,
    )


@router.post("/verify/{version_id}", response_model=IntegrityVerifyResponse)
async def verify_integrity(
    version_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("verify")),
):
    ver_res = await db.execute(select(DocumentVersion).filter_by(id=version_id))
    ver = ver_res.scalars().first()
    if not ver:
        raise ResourceNotFoundException("DocumentVersion", version_id)

    int_res = await db.execute(select(IntegrityRecord).filter_by(version_id=version_id))
    int_rec = int_res.scalars().first()

    # Read current bytes from storage
    current_bytes = await storage_service.read_file(ver.storage_key)
    if current_bytes is None:
        raise HTTPException(status_code=404, detail="Document object is missing from storage.")

    calculated_hash = hashlib.sha256(current_bytes).hexdigest()
    matched = (calculated_hash == ver.sha256_hash) and (not int_rec.is_tampered_simulated if int_rec else True)

    bc_res = await db.execute(select(BlockchainTransaction).filter_by(version_id=version_id))
    bc_tx = bc_res.scalars().first()

    now = datetime.now(timezone.utc)
    if int_rec:
        int_rec.verification_status = "VERIFIED" if matched else "MISMATCH"
        int_rec.last_verified_at = now

    # If mismatch: raise security event & alert per PRD Section 20, 25, 41
    if not matched:
        sec_event = SecurityEvent(
            user_id=current_user.id,
            event_type="INTEGRITY_FAILURE",
            resource_id=version_id,
            risk_score=95,
            severity="CRITICAL",
            description=f"Cryptographic hash mismatch detected on version {version_id}. Expected {ver.sha256_hash}, calculated {calculated_hash}.",
        )
        db.add(sec_event)
        await db.flush()

        sec_alert = SecurityAlert(
            title="CRITICAL: Document Integrity Violation",
            description=f"Automated verification failed for document version {version_id}. Potential unauthorized alteration.",
            severity="HIGH",
            event_id=sec_event.id,
        )
        db.add(sec_alert)

        await record_audit_log(
            db=db,
            actor_id=current_user.id,
            actor_role=current_user.role,
            action="INTEGRITY_FAILURE",
            resource_type="document_version",
            resource_id=version_id,
            result="FAILURE",
            severity="CRITICAL",
            metadata={"expected_hash": ver.sha256_hash, "calculated_hash": calculated_hash},
        )
    else:
        await record_audit_log(
            db=db,
            actor_id=current_user.id,
            actor_role=current_user.role,
            action="INTEGRITY_VERIFICATION",
            resource_type="document_version",
            resource_id=version_id,
            result="SUCCESS",
            severity="INFO",
            metadata={"verified_hash": calculated_hash},
        )

    await db.commit()

    return IntegrityVerifyResponse(
        document_id=ver.document_id,
        version_id=version_id,
        status="VERIFIED" if matched else "INTEGRITY_MISMATCH",
        original_hash=ver.sha256_hash,
        calculated_hash=calculated_hash,
        blockchain_tx_id=bc_tx.transaction_id if bc_tx else None,
        blockchain_block=bc_tx.block_reference if bc_tx else None,
        last_verified_at=now,
        is_tampered_simulated=int_rec.is_tampered_simulated if int_rec else False,
        details="Document matches blockchain registered hash 100%." if matched else "Hash mismatch! Unauthorized alteration detected.",
    )


@router.post("/simulate-tamper/{version_id}", response_model=TamperSimulationResponse)
async def simulate_tamper(
    version_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("verify")),
):
    ver_res = await db.execute(select(DocumentVersion).filter_by(id=version_id))
    ver = ver_res.scalars().first()
    if not ver:
        raise ResourceNotFoundException("DocumentVersion", version_id)

    int_res = await db.execute(select(IntegrityRecord).filter_by(version_id=version_id))
    int_rec = int_res.scalars().first()

    # Tamper file bytes
    try:
        new_hash = await storage_service.simulate_tamper(ver.storage_key)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    if int_rec:
        int_rec.is_tampered_simulated = True
        int_rec.verification_status = "MISMATCH"
        int_rec.tamper_notes = "Simulated byte corruption for presentation / demonstration"

    await record_audit_log(
        db=db,
        actor_id=current_user.id,
        actor_role=current_user.role,
        action="TAMPER_SIMULATION",
        resource_type="document_version",
        resource_id=version_id,
        result="SUCCESS",
        severity="WARNING",
        metadata={"original_hash": ver.sha256_hash, "tampered_hash": new_hash},
    )
    await db.commit()

    return TamperSimulationResponse(
        status="INTEGRITY_MISMATCH",
        original_hash=ver.sha256_hash,
        calculated_hash=new_hash,
        simulated=True,
        message="Simulated payload alteration applied. Verification will now fail.",
    )


@router.post("/restore/{version_id}", response_model=RestoreResponse)
async def restore_tamper(
    version_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("verify")),
):
    ver_res = await db.execute(select(DocumentVersion).filter_by(id=version_id))
    ver = ver_res.scalars().first()
    if not ver:
        raise ResourceNotFoundException("DocumentVersion", version_id)

    int_res = await db.execute(select(IntegrityRecord).filter_by(version_id=version_id))
    int_rec = int_res.scalars().first()

    # Restore file bytes
    try:
        restored_hash = await storage_service.restore_tamper(ver.storage_key)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    if restored_hash != ver.sha256_hash:
        raise IntegrityMismatchException(
            original_hash=ver.sha256_hash,
            calculated_hash=restored_hash,
            message="Canonical storage object does not match the registered document hash.",
        )

    if int_rec:
        int_rec.is_tampered_simulated = False
        int_rec.verification_status = "VERIFIED"
        int_rec.tamper_notes = None

    await record_audit_log(
        db=db,
        actor_id=current_user.id,
        actor_role=current_user.role,
        action="TAMPER_RESTORATION",
        resource_type="document_version",
        resource_id=version_id,
        result="SUCCESS",
        severity="INFO",
        metadata={"restored_hash": restored_hash},
    )
    await db.commit()

    return RestoreResponse(
        status="VERIFIED",
        restored_hash=restored_hash,
        canonical_hash=ver.sha256_hash,
        message="Canonical document state restored. Cryptographic integrity re-verified.",
    )
