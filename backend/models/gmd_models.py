from pydantic import BaseModel, Field, field_validator
from typing import Dict, Any, Optional
from services.gmd_datetime import format_plant_timestamp


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
            value = value.strip()
        return value

    @field_validator("category", "equipment", "verified_by")
    @classmethod
    def reject_empty_required_fields(cls, value, info):
        if not value:
            raise ValueError(f"{info.field_name} is required and cannot be empty.")
        return value

    @field_validator("readings")
    @classmethod
    def validate_readings_not_empty(cls, value):
        if not value:
            raise ValueError("At least one reading is required.")
        return value

    @field_validator("readings")
    @classmethod
    def validate_readings_numeric_and_non_negative(cls, value):
        for parameter, reading_value in value.items():
            if not isinstance(parameter, str) or not parameter.strip():
                raise ValueError("Reading parameter names cannot be empty.")

            if reading_value is None or (isinstance(reading_value, str) and not reading_value.strip()):
                raise ValueError(f"Reading for '{parameter}' cannot be empty.")

            try:
                numeric_value = float(reading_value)
            except (TypeError, ValueError) as exc:
                raise ValueError(
                    f"Reading for '{parameter}' must be numeric; received '{reading_value}'."
                ) from exc

            if numeric_value < 0:
                raise ValueError(
                    f"Reading for '{parameter}' cannot be negative; received {numeric_value}."
                )
        return value


class BulkSubmissionResponse(BaseModel):
    success: bool
    message: str
    rows_appended: int
    timestamp: str = Field(
        default_factory=format_plant_timestamp
    )