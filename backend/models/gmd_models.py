from pydantic import BaseModel, Field, field_validator
from typing import Dict, Any, Optional
from datetime import datetime


class ReadingSubmission(BaseModel):
    timestamp: str
    category: str
    equipment: str
    parameter: str
    location: str
    value: float
    status: str
    verified_by: str
    remarks: str
    entry_source: str


class GMDReadingsRequest(BaseModel):
    category: str = Field(..., min_length=1)
    equipment: str = Field(..., min_length=1)
    readings: Dict[str, Any]
    verified_by: str = Field(..., min_length=1)
    remarks: Optional[str] = ""
    entry_source: Optional[str] = "Field"

    @field_validator("category", "equipment", "verified_by", mode="before")
    @classmethod
    def strip_whitespace(cls, value):
        if isinstance(value, str):
            return value.strip()
        return value

    @field_validator("readings")
    @classmethod
    def validate_readings_not_empty(cls, value):
        if not value:
            raise ValueError("Readings cannot be empty")
        return value


class BulkSubmissionResponse(BaseModel):
    success: bool
    message: str
    rows_appended: int
    timestamp: str = Field(
        default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    )