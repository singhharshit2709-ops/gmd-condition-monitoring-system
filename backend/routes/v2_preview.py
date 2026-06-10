"""V2 preview and submit routes — submit reuses shared validation."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse

from models.v2_preview_models import (
    V2PreviewRequest,
    V2PreviewResponse,
    V2SubmitRequest,
    V2SubmitResponse,
)
from routes.dashboard import get_sheets_service
from services.google_sheets_service import GMDGoogleSheetsService
from services.v2_validation import validate_v2_submission

logger = logging.getLogger("gmd_v2")

router = APIRouter(prefix="/api/v2", tags=["GMD V2"])


@router.post(
    "/preview",
    response_model=V2PreviewResponse,
    status_code=status.HTTP_200_OK,
    summary="Validate a V2 round sheet submission without persisting data",
)
async def preview_v2_submission(payload: V2PreviewRequest) -> V2PreviewResponse:
    """
    Validate category, equipment, and parameter readings against gmd_machine_config_v2.json.
    Does not write to Google Sheets or trigger classification/alarms.
    """
    return validate_v2_submission(payload).preview


@router.post(
    "/submit",
    responses={
        status.HTTP_200_OK: {"model": V2PreviewResponse},
        status.HTTP_201_CREATED: {"model": V2SubmitResponse},
    },
    summary="Validate and persist a V2 round sheet submission to Google Sheets",
)
async def submit_v2_submission(
    payload: V2SubmitRequest,
    service: GMDGoogleSheetsService = Depends(get_sheets_service),
):
    """
    Reuses V2 preview validation. On failure, returns the same validation response (200).
    On success, appends rows to Google Sheets with status NORMAL (no threshold classification).
    """
    outcome = validate_v2_submission(payload)
    if not outcome.preview.success:
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=outcome.preview.model_dump(),
        )

    assert outcome.normalized_readings is not None
    assert outcome.parameter_locations is not None
    assert outcome.category_name is not None
    assert outcome.equipment_name is not None

    try:
        result = service.append_v2_readings(
            category=outcome.category_name,
            equipment=outcome.equipment_name,
            readings=outcome.normalized_readings,
            parameter_locations=outcome.parameter_locations,
            verified_by=payload.verified_by,
            remarks=payload.remarks or "",
            entry_source=payload.entry_source or "Web",
        )
    except RuntimeError as exc:
        logger.error("V2 submit Google Sheets write failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Google Sheets write failed: {exc}",
        ) from exc
    except Exception as exc:
        logger.error("V2 submit unexpected Google Sheets error: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Google Sheets write failed.",
        ) from exc

    reading_count = result.get("rows_appended", len(outcome.normalized_readings))
    submitted_at = result.get("timestamp", "")

    response = V2SubmitResponse(
        success=True,
        equipment=outcome.equipment_name,
        category=outcome.category_name,
        reading_count=reading_count,
        submitted_at=submitted_at,
        message=(
            f"Successfully submitted {reading_count} reading(s) for "
            f"{outcome.equipment_name}."
        ),
    )
    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content=response.model_dump(),
    )
