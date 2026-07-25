"""健康检查 API"""
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from models.database import get_async_session

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health")
async def health_check(session: AsyncSession = Depends(get_async_session)):
    db_ok = False
    try:
        await session.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        pass

    return {
        "status": "ok" if db_ok else "degraded",
        "db": "connected" if db_ok else "disconnected",
        "version": "0.1.0",
    }