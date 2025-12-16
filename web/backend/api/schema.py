"""
Pydantic models that describe transport-layer payloads exposed by the backend.
"""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = Field(..., description="Simple heartbeat indicator.")


class AutocompleteResponse(BaseModel):
    items: List[str] = Field(default_factory=list, description="Matching labels.")


class TrialSummary(BaseModel):
    title: str
    nct_id: str
    organization: Optional[str] = Field(default=None, alias="name")
    user_email: Optional[str] = Field(default=None, alias="email")
    status: Optional[str] = None
    start_date: Optional[datetime] = None
    completion_date: Optional[datetime] = None
    reporting_due_date: Optional[datetime] = None

    class Config:
        populate_by_name = True
