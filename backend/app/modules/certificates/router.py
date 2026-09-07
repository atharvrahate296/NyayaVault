import uuid
from datetime import datetime, timezone
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db, record_audit_log, require_permission
from app.config.settings import settings
from app.core.exceptions.handlers import ResourceNotFoundException, IntegrityMismatchException
from app.db.models import Certificate, Document, DocumentVersion, IntegrityRecord, BlockchainTransaction, Case, User
from app.modules.certificates.schemas import CertificateCreateRequest, CertificateResponse
from app.modules.certificates.service import CertificateService
from app.modules.storage.service import storage_service

router = APIRouter(prefix="/certificates", tags=["Section 65B Certificates"])


@router.get("", response_model=List[CertificateResponse])
async def list_certificates(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Certificate).order_by(Certificate.created_at.desc()))
    return result.scalars().all()


@router.post("/generate", response_model=CertificateResponse, status_code=status.HTTP_201_CREATED)
async def generate_certificate(
    req: CertificateCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("generate_certificate")),
):
    # Fetch case
    case_res = await db.execute(select(Case).filter_by(id=req.case_id))
    case_obj = case_res.scalars().first()
    if not case_obj:
        raise ResourceNotFoundException("Case", req.case_id)

    doc_title = "Digital Evidence Record"
    doc_hash = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    bc_tx_id = "0x4f8a...771b"

    if req.document_id:
        doc_res = await db.execute(select(Document).filter_by(id=req.document_id))
        doc_obj = doc_res.scalars().first()
        if not doc_obj:
            raise ResourceNotFoundException("Document", req.document_id)
        doc_title = doc_obj.title

        # Check integrity record
        int_res = await db.execute(select(IntegrityRecord).filter_by(document_id=req.document_id))
        int_rec = int_res.scalars().first()
        if int_rec:
            if int_rec.verification_status == "MISMATCH" or int_rec.is_tampered_simulated:
                raise IntegrityMismatchException(
                    original_hash=int_rec.sha256_hash,
                    calculated_hash="ALTERED",
                    message="Cannot generate Section 65B Certificate: Document integrity verification failed!",
                )
            doc_hash = int_rec.sha256_hash

        # Get blockchain TX
        bc_res = await db.execute(select(BlockchainTransaction).filter_by(document_id=req.document_id))
        bc_tx = bc_res.scalars().first()
        if bc_tx:
            bc_tx_id = bc_tx.transaction_id

    cert_num = f"CERT-65B-{datetime.now().year}-{uuid.uuid4().hex[:8].upper()}"
    now_str = datetime.now(timezone.utc).strftime("%d-%b-%Y %H:%M:%S UTC")

    # Generate PDF bytes
    pdf_bytes = CertificateService.generate_section_65b_pdf(
        cert_number=cert_num,
        case_number=case_obj.case_number,
        doc_title=doc_title,
        sha256_hash=doc_hash,
        officer_name=current_user.full_name,
        department=current_user.department,
        blockchain_tx=bc_tx_id,
        timestamp=now_str,
    )

    cert_storage_key = f"certificates/{cert_num}.pdf"
    await storage_service.save_file(
        pdf_bytes,
        cert_storage_key,
        content_type="application/pdf",
        metadata={"certificate_number": cert_num, "canonical": "false"},
    )

    cert = Certificate(
        certificate_number=cert_num,
        case_id=req.case_id,
        document_id=req.document_id,
        evidence_id=req.evidence_id,
        generated_by=current_user.id,
        file_storage_key=cert_storage_key,
        verification_hash=doc_hash,
    )
    db.add(cert)

    await record_audit_log(
        db=db,
        actor_id=current_user.id,
        actor_role=current_user.role,
        action="CERTIFICATE_GENERATION",
        resource_type="certificate",
        resource_id=cert.certificate_number,
        case_id=req.case_id,
        result="SUCCESS",
        metadata={"cert_number": cert_num, "hash": doc_hash},
    )
    await db.commit()
    await db.refresh(cert)
    return cert


@router.get("/{certificate_id}/download")
async def download_certificate(
    certificate_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    res = await db.execute(select(Certificate).filter_by(id=certificate_id))
    cert = res.scalars().first()
    if not cert:
        # Check by cert_number
        res2 = await db.execute(select(Certificate).filter_by(certificate_number=certificate_id))
        cert = res2.scalars().first()
        if not cert:
            raise ResourceNotFoundException("Certificate", certificate_id)

    pdf_bytes = await storage_service.read_file(cert.file_storage_key)
    if pdf_bytes is None:
        raise HTTPException(status_code=404, detail="Certificate object is missing from storage.")

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{cert.certificate_number}.pdf"'},
    )

@router.get("/{certificate_id}/download-url")
async def create_certificate_download_url(
    certificate_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("download")),
):
    res = await db.execute(select(Certificate).filter_by(id=certificate_id))
    cert = res.scalars().first()
    if not cert:
        res = await db.execute(select(Certificate).filter_by(certificate_number=certificate_id))
        cert = res.scalars().first()
    if not cert:
        raise ResourceNotFoundException("Certificate", certificate_id)

    url = await storage_service.create_download_url(
        cert.file_storage_key,
        f"{cert.certificate_number}.pdf",
        "application/pdf",
    )
    await record_audit_log(
        db=db,
        actor_id=current_user.id,
        actor_role=current_user.role,
        action="CERTIFICATE_DOWNLOAD_URL_CREATED",
        resource_type="certificate",
        resource_id=cert.certificate_number,
        case_id=cert.case_id,
        result="SUCCESS",
        metadata={"file_name": f"{cert.certificate_number}.pdf"},
    )
    await db.commit()
    return {
        "url": url,
        "expires_in": settings.STORAGE_PRESIGNED_URL_TTL,
        "file_name": f"{cert.certificate_number}.pdf",
    }
