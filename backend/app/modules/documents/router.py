import io
import uuid
from typing import List, Optional
from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    get_current_user,
    get_db,
    record_audit_log,
    require_permission,
    require_clearance,
)
from app.core.exceptions.handlers import ResourceNotFoundException, AccessDeniedException
from app.db.models import (
    Document,
    DocumentVersion,
    StorageObject,
    IntegrityRecord,
    BlockchainTransaction,
    Case,
    User,
)
from app.modules.documents.schemas import (
    DocumentResponse,
    DocumentVersionResponse,
    DocumentUpdate,
)
from app.config.settings import settings
from app.modules.storage.service import storage_service
from app.workers.async_tasks import process_document_pipeline

router = APIRouter(prefix="/documents", tags=["Documents"])


@router.get("", response_model=List[DocumentResponse])
async def list_documents(
    case_id: Optional[str] = None,
    document_type: Optional[str] = None,
    classification: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = select(Document)
    if case_id:
        query = query.filter_by(case_id=case_id)
    if document_type:
        query = query.filter_by(document_type=document_type)
    if classification:
        query = query.filter_by(classification=classification)

    # ABAC: Clearance filter
    if current_user.clearance_level == "Level 1":
        query = query.filter(Document.classification.in_(["Public", "Restricted"]))
    elif current_user.clearance_level in ["Level 2", "Level 3"]:
        query = query.filter(Document.classification != "Top Secret")

    query = query.order_by(Document.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    docs = result.scalars().all()

    response_list = []
    for d in docs:
        d_resp = DocumentResponse.model_validate(d)
        if d.current_version_id:
            v_res = await db.execute(select(DocumentVersion).filter_by(id=d.current_version_id))
            ver = v_res.scalars().first()
            if ver:
                d_resp.latest_version = DocumentVersionResponse.model_validate(ver)
        response_list.append(d_resp)
    return response_list


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Document).filter_by(id=document_id))
    doc = result.scalars().first()
    if not doc:
        raise ResourceNotFoundException("Document", document_id)

    # ABAC Clearance check
    if doc.classification == "Top Secret" and current_user.clearance_level != "Level 4":
        raise AccessDeniedException("Top Secret document requires Level 4 clearance.")

    d_resp = DocumentResponse.model_validate(doc)
    if doc.current_version_id:
        v_res = await db.execute(select(DocumentVersion).filter_by(id=doc.current_version_id))
        ver = v_res.scalars().first()
        if ver:
            d_resp.latest_version = DocumentVersionResponse.model_validate(ver)
    return d_resp


@router.post("", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    case_id: str = Form(...),
    document_type: str = Form(...),
    classification: str = Form("Confidential"),
    description: Optional[str] = Form(None),
    title: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("upload")),
):
    # Verify case exists
    case_res = await db.execute(select(Case).filter_by(id=case_id))
    case_obj = case_res.scalars().first()
    if not case_obj:
        raise ResourceNotFoundException("Case", case_id)

    # Read uploaded bytes
    content = await file.read()
    if len(content) == 0:
        raise HTTPException(status_code=400, detail="Cannot upload empty file.")

    doc_id = f"doc_{uuid.uuid4().hex[:12]}"
    ver_id = f"ver_{uuid.uuid4().hex[:12]}"
    filename = file.filename or f"doc_{doc_id}.pdf"
    storage_key = f"cases/{case_id}/documents/{doc_id}/versions/{ver_id}/{filename}"

    # 1. Save to secure storage & compute SHA-256
    mime_type = file.content_type or "application/octet-stream"
    s_key, size, sha256_hash = await storage_service.save_file(
        content,
        storage_key,
        content_type=mime_type,
        metadata={"document_id": doc_id, "version_id": ver_id},
    )

    # 2. Persist Document & Version records
    new_doc = Document(
        id=doc_id,
        case_id=case_id,
        document_type=document_type,
        title=title or filename,
        description=description,
        classification=classification,
        current_version_id=ver_id,
        owner_id=current_user.id,
        status="Active",
    )
    db.add(new_doc)
    await db.flush()

    new_ver = DocumentVersion(
        id=ver_id,
        document_id=doc_id,
        version_number=1,
        storage_key=s_key,
        sha256_hash=sha256_hash,
        file_name=filename,
        file_size=size,
        mime_type=mime_type,
        created_by=current_user.id,
        change_reason="Initial upload",
        status="ACTIVE",
    )
    db.add(new_ver)

    storage_obj = StorageObject(
        version_id=ver_id,
        storage_provider=settings.STORAGE_PROVIDER,
        bucket=settings.STORAGE_BUCKET,
        storage_key=s_key,
        canonical_bucket=settings.STORAGE_BACKUP_BUCKET,
        canonical_key=s_key,
        mime_type=file.content_type or "application/pdf",
        file_size=size,
        is_tampered_simulated=False,
    )
    db.add(storage_obj)

    # 3. Register Integrity Record
    integrity_rec = IntegrityRecord(
        document_id=doc_id,
        version_id=ver_id,
        sha256_hash=sha256_hash,
        verification_status="VERIFIED",
        is_tampered_simulated=False,
    )
    db.add(integrity_rec)

    # 4. Register on Blockchain ledger
    tx_id = f"0x{uuid.uuid4().hex}{uuid.uuid4().hex}"[:66]
    bc_tx = BlockchainTransaction(
        document_id=doc_id,
        version_id=ver_id,
        sha256=sha256_hash,
        transaction_id=tx_id,
        block_reference=f"Block #{uuid.uuid4().int % 90000 + 10000}",
        network="Hyperledger Fabric v2.5",
        channel="nyayachannel",
        status="COMMITTED",
    )
    db.add(bc_tx)

    # 5. Record Audit Event
    await record_audit_log(
        db=db,
        actor_id=current_user.id,
        actor_role=current_user.role,
        action="DOCUMENT_UPLOAD",
        resource_type="document",
        resource_id=doc_id,
        case_id=case_id,
        result="SUCCESS",
        metadata={
            "file_name": filename,
            "sha256": sha256_hash,
            "size": size,
            "tx_id": tx_id,
        },
    )
    await db.commit()
    await db.refresh(new_doc)

    # 6. Queue Async AI / OCR Pipeline & Search Indexing
    background_tasks.add_task(process_document_pipeline, doc_id, ver_id, content, filename, case_id)

    d_resp = DocumentResponse.model_validate(new_doc)
    d_resp.latest_version = DocumentVersionResponse.model_validate(new_ver)
    return d_resp


@router.post("/{document_id}/versions", response_model=DocumentResponse)
async def create_document_version(
    document_id: str,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    change_reason: str = Form("Updated version"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("upload")),
):
    doc_res = await db.execute(select(Document).filter_by(id=document_id))
    doc = doc_res.scalars().first()
    if not doc:
        raise ResourceNotFoundException("Document", document_id)

    # Fetch max version number
    v_res = await db.execute(
        select(DocumentVersion).filter_by(document_id=document_id).order_by(DocumentVersion.version_number.desc())
    )
    existing_versions = v_res.scalars().all()
    next_ver_num = (existing_versions[0].version_number + 1) if existing_versions else 1

    content = await file.read()
    ver_id = f"ver_{uuid.uuid4().hex[:12]}"
    filename = file.filename or f"doc_{document_id}_v{next_ver_num}.pdf"
    storage_key = f"cases/{doc.case_id}/documents/{document_id}/versions/{ver_id}/{filename}"

    mime_type = file.content_type or "application/pdf"
    s_key, size, sha256_hash = await storage_service.save_file(
        content,
        storage_key,
        content_type=mime_type,
        metadata={"document_id": document_id, "version_id": ver_id},
    )

    new_ver = DocumentVersion(
        id=ver_id,
        document_id=document_id,
        version_number=next_ver_num,
        storage_key=s_key,
        sha256_hash=sha256_hash,
        file_name=filename,
        file_size=size,
        mime_type=mime_type,
        created_by=current_user.id,
        change_reason=change_reason,
        status="ACTIVE",
    )
    db.add(new_ver)

    doc.current_version_id = ver_id
    doc.updated_at = new_ver.created_at

    # Register integrity & blockchain
    int_rec = IntegrityRecord(
        document_id=document_id,
        version_id=ver_id,
        sha256_hash=sha256_hash,
        verification_status="VERIFIED",
    )
    db.add(int_rec)

    tx_id = f"0x{uuid.uuid4().hex}{uuid.uuid4().hex}"[:66]
    bc_tx = BlockchainTransaction(
        document_id=document_id,
        version_id=ver_id,
        sha256=sha256_hash,
        transaction_id=tx_id,
        block_reference=f"Block #{uuid.uuid4().int % 90000 + 10000}",
        status="COMMITTED",
    )
    db.add(bc_tx)

    await record_audit_log(
        db=db,
        actor_id=current_user.id,
        actor_role=current_user.role,
        action="VERSION_CREATION",
        resource_type="document",
        resource_id=document_id,
        case_id=doc.case_id,
        result="SUCCESS",
        metadata={"version_number": next_ver_num, "sha256": sha256_hash},
    )
    await db.commit()
    await db.refresh(doc)

    background_tasks.add_task(process_document_pipeline, document_id, ver_id, content, filename, doc.case_id)

    d_resp = DocumentResponse.model_validate(doc)
    d_resp.latest_version = DocumentVersionResponse.model_validate(new_ver)
    return d_resp


@router.get("/{document_id}/versions", response_model=List[DocumentVersionResponse])
async def list_document_versions(
    document_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(DocumentVersion).filter_by(document_id=document_id).order_by(DocumentVersion.version_number.desc())
    )
    return result.scalars().all()


@router.get("/{document_id}/download")
async def download_document(
    document_id: str,
    version_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("download")),
):
    doc_res = await db.execute(select(Document).filter_by(id=document_id))
    doc = doc_res.scalars().first()
    if not doc:
        raise ResourceNotFoundException("Document", document_id)

    target_ver_id = version_id or doc.current_version_id
    ver_res = await db.execute(select(DocumentVersion).filter_by(id=target_ver_id))
    ver = ver_res.scalars().first()
    if not ver:
        raise ResourceNotFoundException("DocumentVersion", target_ver_id)

    bytes_data = await storage_service.read_file(ver.storage_key)
    if bytes_data is None:
        raise HTTPException(status_code=404, detail="Document object is missing from storage.")

    await record_audit_log(
        db=db,
        actor_id=current_user.id,
        actor_role=current_user.role,
        action="DOCUMENT_DOWNLOAD",
        resource_type="document",
        resource_id=document_id,
        case_id=doc.case_id,
        result="SUCCESS",
        metadata={"version_id": target_ver_id, "file_name": ver.file_name},
    )
    await db.commit()

    return Response(
        content=bytes_data,
        media_type=ver.mime_type,
        headers={"Content-Disposition": f'attachment; filename="{ver.file_name}"'},
    )

@router.get("/{document_id}/download-url")
async def create_document_download_url(
    document_id: str,
    version_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("download")),
):
    doc_res = await db.execute(select(Document).filter_by(id=document_id))
    doc = doc_res.scalars().first()
    if not doc:
        raise ResourceNotFoundException("Document", document_id)
    if doc.classification == "Top Secret" and current_user.clearance_level != "Level 4":
        raise AccessDeniedException("Top Secret document requires Level 4 clearance.")

    target_ver_id = version_id or doc.current_version_id
    ver_res = await db.execute(select(DocumentVersion).filter_by(id=target_ver_id))
    ver = ver_res.scalars().first()
    if not ver:
        raise ResourceNotFoundException("DocumentVersion", target_ver_id)

    url = await storage_service.create_download_url(ver.storage_key, ver.file_name, ver.mime_type)
    await record_audit_log(
        db=db,
        actor_id=current_user.id,
        actor_role=current_user.role,
        action="DOCUMENT_DOWNLOAD_URL_CREATED",
        resource_type="document",
        resource_id=document_id,
        case_id=doc.case_id,
        result="SUCCESS",
        metadata={"version_id": target_ver_id, "file_name": ver.file_name},
    )
    await db.commit()
    return {"url": url, "expires_in": settings.STORAGE_PRESIGNED_URL_TTL, "file_name": ver.file_name}
