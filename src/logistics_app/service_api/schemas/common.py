"""Common API schemas."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class ApiErrorResponse(BaseModel):
    """Standard API error body."""

    detail: str


class OrmResponseModel(BaseModel):
    """Base response model configured for ORM object conversion."""

    model_config = ConfigDict(from_attributes=True)
