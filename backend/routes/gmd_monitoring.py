import logging
from fastapi import APIRouter, HTTPException, Depends, status
from models.gmd_models import GMDReadingsRequest, BulkSubmissionResponse
from gmd_config import validate_gmd_submission
from services.gmd_datetime import log_submission_timestamp
from services.google_sheets_service import GMDGoogleSheetsService

# Configure structured routing logger matching core systems
logger = logging.getLogger("gmd_logger")
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] [GMD-ROUTER]: %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

router = APIRouter(prefix="/gmd/condition-monitoring", tags=["GMD Condition Monitoring"])

def get_sheets_service() -> GMDGoogleSheetsService:
    """Dependency provider for the single-source-of-truth Google Sheets service engine."""
    return GMDGoogleSheetsService()

@router.post(
    "/bulk", 
    response_model=BulkSubmissionResponse, 
    status_code=status.HTTP_201_CREATED,
    summary="Ingest dynamic multi-parameter operational readings batch"
)
async def submit_bulk_readings(
    payload: GMDReadingsRequest, 
    service: GMDGoogleSheetsService = Depends(get_sheets_service)
) -> BulkSubmissionResponse:
    """
    Accepts, validates, and dynamically transforms telemetry packets submitted by the client
    into flat operational logs committed directly to the centralized data sheets partition.
    """
    logger.info(f"Received batch transmission request for category: '{payload.category}', asset: '{payload.equipment}'")

    try:
        validate_gmd_submission(
            category=payload.category,
            equipment=payload.equipment,
            readings=payload.readings,
            verified_by=payload.verified_by,
        )
    except ValueError as validation_err:
        logger.warning("Bulk submission rejected: %s", validation_err)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(validation_err),
        ) from validation_err

    try:
        # Process and unpack flat field measurements directly via schema loops
        result = service.append_readings(
            category=payload.category,
            equipment=payload.equipment,
            readings=payload.readings,
            verified_by=payload.verified_by,
            remarks=payload.remarks or "",
            entry_source=payload.entry_source or "Field"
        )
        
        rows_committed: int = result.get("rows_appended", 0)
        logger.info(f"Committed {rows_committed} discrete log rows safely to tracking workbook.")
        
        return BulkSubmissionResponse(
            success=True,
            message=f"Successfully logged {rows_committed} metric records for asset unit '{payload.equipment}'.",
            rows_appended=rows_committed,
            timestamp=log_submission_timestamp("GMD bulk submit response"),
        )

    except ValueError as schema_err:
        # Handle structural mismatch anomalies, unrecognized identifiers, and serialization errors
        logger.error(f"Unprocessable entity formatting mismatch caught processing payload: {str(schema_err)}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Schema mapping verification failed: {str(schema_err)}"
        )
        
    except RuntimeError as run_err:
        # Fixed: Explicitly retaining the 500 status code requirement for ledger synchronization failures
        logger.critical(f"Upstream persistent ledger driver integration reported connectivity loss: {str(run_err)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Downstream transaction broker synchronization failure: {str(run_err)}"
        )
        
    except Exception as system_err:
        # Catch-all execution wrapper protecting process threads from unhandled runtime exit events
        logger.critical(f"Unhandled internal server exception intercepted during data parse thread: {str(system_err)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal application transaction failure encountered. Check routing infrastructure logs."
        )