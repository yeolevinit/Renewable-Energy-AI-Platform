"""Dashboard overview endpoint."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.services.overview_service import get_overview

router = APIRouter(prefix="/overview", tags=["Overview"])


@router.get("")
def overview(db: Session = Depends(get_db)):
    """
    Return a consolidated summary of the platform state for the dashboard.
    Includes generation data coverage, pipeline status, quality score,
    alert counts, and best model metrics.
    """
    return get_overview(db)
