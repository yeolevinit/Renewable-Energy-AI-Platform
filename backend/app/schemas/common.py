"""Shared Pydantic schema types."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Generic, List, Optional, TypeVar

from pydantic import BaseModel, ConfigDict

T = TypeVar("T")


class HealthResponse(BaseModel):
    status: str
    version: str
    database_connected: bool
    timestamp: datetime


class PaginatedResponse(BaseModel, Generic[T]):
    items: List[T]
    total: int
    page: int
    page_size: int


class MessageResponse(BaseModel):
    message: str
    details: Optional[Dict[str, Any]] = None
