from pydantic import BaseModel, Field, field_validator
from typing import Any, Dict, List, Optional


class V2PreviewRequest(BaseModel):
    category: str = Field(..., min_length=1)
    equipment: str = Field(..., min_length=1)
    readings: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("category", "equipment", mode="before")
    @classmethod
    def strip_whitespace(cls, value: Any) -> Any:
        if isinstance(value, str):
            return value.strip()
        return value


class InvalidParameterDetail(BaseModel):
    key: str
    reason: str


class MissingParameterDetail(BaseModel):
    key: str
    display_full_label: str = ""


class V2PreviewResponse(BaseModel):
    success: bool
    expected_readings: int
    received_readings: int
    missing_parameters: List[MissingParameterDetail]
    invalid_parameters: List[InvalidParameterDetail]
    validation_message: str


class V2SubmitRequest(V2PreviewRequest):
    verified_by: str = ""
    remarks: str = ""
    entry_source: str = "Web"

    @field_validator("verified_by", "remarks", "entry_source", mode="before")
    @classmethod
    def strip_optional_text(cls, value: Any) -> Any:
        if isinstance(value, str):
            return value.strip()
        return value


class V2SubmitResponse(BaseModel):
    success: bool = True
    equipment: str
    category: str
    reading_count: int
    submitted_at: str
    message: str
