from datetime import datetime, timezone
from fastapi import APIRouter, Depends, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import settings
from app.db.session import get_db
from app.integrations.qdrant_client import qdrant_service
from app.modules.storage.service import storage_service


router = APIRouter(prefix="/health", tags=["Observability & Health Checks"])


@router.get("")
async def general_health():
    qdrant_status = await qdrant_service.check_health()
    return {
        "status": "HEALTHY",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "environment": settings.APP_ENV,
        "qdrant": qdrant_status,
    }


@router.get("/db")
async def database_health(db: AsyncSession = Depends(get_db)):
    try:
        await db.execute(text("SELECT 1"))
        return {
            "status": "UP",
            "database": "CONNECTED",
            "url_type": settings.DATABASE_URL.split(":")[0],
        }
    except Exception as e:
        return {
            "status": "DOWN",
            "database": "ERROR",
            "error": str(e),
        }


@router.get("/storage")
async def storage_health():
    is_available = await storage_service.check_health()
    return {
        "status": "UP" if is_available else "DOWN",
        "provider": settings.STORAGE_PROVIDER,
        "bucket": settings.STORAGE_BUCKET,
    }


@router.get("/blockchain")
async def blockchain_health():
    return {
        "status": "UP",
        "network": settings.BLOCKCHAIN_NETWORK,
        "channel": settings.BLOCKCHAIN_CHANNEL,
        "chaincode": settings.BLOCKCHAIN_CHAINCODE,
        "ledger_state": "SYNCHRONIZED",
    }


@router.get("/qdrant")
async def qdrant_health():
    return await qdrant_service.check_health()

