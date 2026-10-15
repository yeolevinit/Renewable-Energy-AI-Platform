"""Data source management endpoints."""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.data_source import DataSource
from app.schemas.pipeline import DataSourceCreate, DataSourceResponse

router = APIRouter(prefix="/sources", tags=["Data Sources"])


@router.get("", response_model=List[DataSourceResponse])
def list_sources(db: Session = Depends(get_db)):
    """Return all registered data sources."""
    return db.query(DataSource).filter(DataSource.is_active == True).all()


@router.get("/{source_id}", response_model=DataSourceResponse)
def get_source(source_id: int, db: Session = Depends(get_db)):
    src = db.query(DataSource).filter(DataSource.id == source_id).first()
    if not src:
        raise HTTPException(status_code=404, detail="Data source not found")
    return src


@router.post("", response_model=DataSourceResponse, status_code=status.HTTP_201_CREATED)
def create_source(payload: DataSourceCreate, db: Session = Depends(get_db)):
    """Register a new data source."""
    existing = db.query(DataSource).filter(DataSource.name == payload.name).first()
    if existing:
        raise HTTPException(status_code=409, detail="A source with this name already exists")
    src = DataSource(**payload.model_dump())
    db.add(src)
    db.flush()
    return src


@router.delete("/{source_id}", status_code=status.HTTP_204_NO_CONTENT)
def deactivate_source(source_id: int, db: Session = Depends(get_db)):
    """Soft-delete (deactivate) a data source."""
    src = db.query(DataSource).filter(DataSource.id == source_id).first()
    if not src:
        raise HTTPException(status_code=404, detail="Data source not found")
    src.is_active = False
