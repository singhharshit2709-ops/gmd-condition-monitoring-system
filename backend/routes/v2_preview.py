"""V2 preview and submit routes — submit reuses shared validation."""

from __future__ import annotations

import logging
from functools import lru_cache

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse

from models.v2_preview_models import (
    V2PreviewRequest,
    V2PreviewResponse,
    V2SubmitRequest,
    V2SubmitResponse,
)
from routes.dashboard import get_sheets_service, invalidate_all_dashboard_cache
from services.google_drive_service import GoogleDriveMediaService
from services.google_sheets_service import GMDGoogleSheetsService
from services.media_utils import parse_submission_media
from services.v2_validation import validate_v2_submission

logger = logging.getLogger("gmd_v2")

router = APIRouter(prefix="/api/v2", tags=["GMD V2"])


@lru_cache(maxsize=1)
def get_drive_media_service() -> GoogleDriveMediaService:
    return GoogleDriveMediaService()


def _resolve_submission_media(
    payload: V2SubmitRequest,
    drive_service: GoogleDriveMediaService,
    *,
    category: str,
    equipment: str,
) -> tuple[str, str, str]:
    """Upload attached media when present. Returns (name, type, url)."""
    if not payload.has_media_attachment():
        return "", "", ""

    try:
        file_bytes, mime_type, filename = parse_submission_media(
            payload.media_data,
            media_type=payload.media_type,
            media_name=payload.media_name,
        )
    except ValueError as exc:
        logger.error("Invalid submission media payload: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid media attachment: {exc}",
        ) from exc

    try:
        media_url = drive_service.upload_submission_media(
            file_bytes,
            filename,
            mime_type,
            category=category,
            equipment=equipment,
        )
    except Exception as exc:
        logger.error(
            "Media upload failed for equipment=%r category=%r filename=%r: %s",
            equipment,
            category,
            filename,
            exc,
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Media upload failed: {exc}",
        ) from exc

    logger.info(
        "Generated Drive URL for submission equipment=%r category=%r url=%s",
        equipment,
        category,
        media_url,
    )
    return filename, mime_type, media_url


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
    drive_service: GoogleDriveMediaService = Depends(get_drive_media_service),
):
    """
    Reuses V2 preview validation. On failure, returns the same validation response (200).
    On success, uploads optional media to Google Drive, then appends rows to Google Sheets.
    """
    outcome = validate_v2_submission(payload)
    if not outcome.preview.success:
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=outcome.preview.model_dump(),
        )

    assert outcome.normalized_readings is not None
    assert outcome.parameter_locations is not None
    assert outcome.parameter_units is not None
    assert outcome.category_name is not None
    assert outcome.equipment_name is not None

    media_name = ""
    media_type = ""
    media_url = ""

    if payload.has_media_attachment():
        media_name, media_type, media_url = _resolve_submission_media(
            payload,
            drive_service,
            category=outcome.category_name,
            equipment=outcome.equipment_name,
        )

    submission_id = payload.submission_id.strip() if payload.submission_id else ""

    logger.info(
        "V2 submit persistence starting area_tank=%r category=%r equipment=%r tag_no=%r "
        "submission_id=%r readings=%d has_media=%s media_url=%r",
        payload.area_tank,
        outcome.category_name,
        outcome.equipment_name,
        payload.tag_no,
        submission_id or "(generated)",
        len(outcome.normalized_readings),
        payload.has_media_attachment(),
        media_url or None,
    )

    try:
        result = service.append_v2_readings(
            category=outcome.category_name,
            equipment=outcome.equipment_name,
            readings=outcome.normalized_readings,
            parameter_locations=outcome.parameter_locations,
            verified_by=payload.verified_by,
            remarks=payload.remarks or "",
            entry_source=payload.entry_source or "Web",
            media_name=media_name,
            media_type=media_type,
            media_url=media_url,
            area_tank=payload.area_tank,
            tag_no=payload.tag_no,
            parameter_units=outcome.parameter_units,
            submission_id=submission_id,
        )
    except RuntimeError as exc:
        logger.error(
            "V2 submit Google Sheets write failed after media_url=%r: %s",
            media_url or None,
            exc,
        )
        detail = f"Google Sheets write failed: {exc}"
        if media_url:
            detail = (
                f"Media was uploaded to Google Drive ({media_url}) but Google Sheets "
                f"persistence failed: {exc}"
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=detail,
        ) from exc
    except Exception as exc:
        logger.error(
            "V2 submit unexpected Google Sheets error after media_url=%r: %s",
            media_url or None,
            exc,
            exc_info=True,
        )
        detail = "Google Sheets write failed."
        if media_url:
            detail = (
                f"Media was uploaded to Google Drive ({media_url}) but Google Sheets "
                f"persistence failed: {exc}"
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=detail,
        ) from exc

    reading_count = int(result.get("rows_appended") or 0)
    submitted_at = str(result.get("timestamp") or "").strip()
    resolved_submission_id = result.get("submission_id", submission_id)

    if reading_count <= 0:
        logger.error(
            "V2 submit persistence reported zero rows appended area_tank=%r equipment=%r",
            payload.area_tank,
            outcome.equipment_name,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Google Sheets write failed: no rows were appended.",
        )

    if not submitted_at:
        logger.error(
            "V2 submit persistence missing timestamp area_tank=%r equipment=%r",
            payload.area_tank,
            outcome.equipment_name,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Google Sheets write failed: missing submission timestamp.",
        )

    get_sheets_service.cache_clear()
    invalidate_all_dashboard_cache()
    logger.info(
        "V2 submit persistence completed rows_appended=%d submission_id=%s "
        "area_tank=%r equipment=%r tag_no=%r submitted_at=%s dashboard_cache_invalidated=true",
        reading_count,
        resolved_submission_id,
        payload.area_tank,
        outcome.equipment_name,
        payload.tag_no,
        submitted_at,
    )

    response = V2SubmitResponse(
        success=True,
        equipment=outcome.equipment_name,
        category=outcome.category_name,
        reading_count=reading_count,
        submitted_at=submitted_at,
        submission_id=resolved_submission_id,
        message=(
            f"Successfully submitted {reading_count} reading(s) for "
            f"{outcome.equipment_name}."
        ),
    )
    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content=response.model_dump(),
    )
