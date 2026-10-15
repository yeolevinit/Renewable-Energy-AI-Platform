"""Health check endpoint."""

from datetime import datetime, timezone

from fastapi import APIRouter

from app.core.config import get_settings
from app.db.database import check_connection
from app.schemas.common import HealthResponse

router = APIRouter()
settings = get_settings()


@router.get("/health", response_model=HealthResponse, tags=["System"])
async def health_check() -> HealthResponse:
    """Return application health status and database connectivity."""
    return HealthResponse(
        status="ok",
        version=settings.app_version,
        database_connected=check_connection(),
        timestamp=datetime.now(timezone.utc),
    )
