# app/modules/reports/router.py

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from typing import Optional, List
from fastapi.responses import StreamingResponse

from app.db.dependencies import get_db
from app.db.models import User

from app.modules.users.router import get_current_user, admin_required
from app.modules.reports.schemas import (
    ReportCreate,
    ReportUpdate,
    ReportResponse,
    ReportMetricsResponse,
    BulkDeleteRequest,
    BulkDeleteResponse,
    UniquenessBenchmarkRequest,
    UniquenessBenchmarkResponse,
)
from app.modules.reports.intake_schema import LifeSignifyRequest

from app.modules.reports.service import (
    create_report,
    generate_ai_report_service,
    get_report_blueprint,
    get_reports,
    get_report,
    get_radar_data,
    update_report,
    soft_delete_report,
    restore_report,
    hard_delete_report,
    export_report_pdf,
    get_report_metrics,
    bulk_delete_reports,
    generate_uniqueness_benchmark_service,
)

router = APIRouter(tags=["Reports"])


# =====================================================
# CREATE MANUAL REPORT
# =====================================================
@router.post("/", response_model=ReportResponse)
def create_new_report(
    report: ReportCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Create a manually crafted report
    """
    return create_report(
        db=db,
        current_user=current_user,
        title=report.title,
        content=report.content.dict() if hasattr(report.content, "dict") else report.content,
    )


# =====================================================
# GENERATE AI REPORT (PLAN-AWARE)
# =====================================================
@router.post("/generate-ai-report", response_model=ReportResponse)
def generate_ai_report(
    request: LifeSignifyRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Generate an AI-powered numerology report
    - Respects plan limits
    - Enriches content based on plan tier
    - Returns complete report structure
    """
    intake_data = request.model_dump()
    return generate_ai_report_service(
        db=db,
        current_user=current_user,
        intake_data=intake_data,
    )


# =====================================================
# LIST REPORTS (WITH PAGINATION)
# =====================================================
@router.get("/", response_model=List[ReportResponse])
def list_reports(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=500, description="Max records to return"),
    include_deleted: bool = Query(False, description="Include soft-deleted reports (admin only)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List all reports for current user with pagination
    """
    # Only admins can see deleted reports
    if include_deleted and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    return get_reports(
        db=db, 
        current_user=current_user,
        skip=skip,
        limit=limit,
        include_deleted=include_deleted,
    )


# =====================================================
# GET REPORT METRICS
# =====================================================
@router.get("/metrics/usage", response_model=ReportMetricsResponse)
def get_usage_metrics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get report usage metrics for current user
    - Total reports
    - Plan usage
    - Remaining report credits
    """
    return get_report_metrics(db=db, current_user=current_user)



# =====================================================
# GET TIER BLUEPRINT
# =====================================================
@router.get("/blueprint/tiers")
def get_tier_blueprint(
    plan_name: Optional[str] = Query(None, description="Optional plan name: basic/standard/enterprise"),
):
    """
    Get report section blueprint by plan tier
    - Without plan_name: returns all tiers
    - With plan_name: returns one tier blueprint
    """
    return get_report_blueprint(plan_name=plan_name)


# =====================================================
# ADMIN DEBUG: UNIQUENESS BENCHMARK
# =====================================================
@router.post("/admin/debug/uniqueness-benchmark", response_model=UniquenessBenchmarkResponse)
def run_uniqueness_benchmark(
    request: UniquenessBenchmarkRequest,
    current_user: User = Depends(admin_required),
):
    """
    Admin-only deterministic benchmark to verify plan-wise report uniqueness
    across generated sample users.
    """
    _ = current_user
    return generate_uniqueness_benchmark_service(
        user_count=request.user_count,
        target_difference=request.target_difference,
    )

# =====================================================
# GET SINGLE REPORT
# =====================================================
@router.get("/{report_id}", response_model=ReportResponse)
def get_single_report(
    report_id: int,
    include_deleted: bool = Query(False, description="Include if deleted (admin only)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get a single report by ID
    """
    # Only admins can see deleted reports
    if include_deleted and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    return get_report(
        db=db, 
        current_user=current_user, 
        report_id=report_id,
        include_deleted=include_deleted,
    )


# =====================================================
# GET RADAR DATA
# =====================================================
@router.get("/{report_id}/radar")
def fetch_radar_data(
    report_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get radar chart data for visualization
    """
    return get_radar_data(db=db, current_user=current_user, report_id=report_id)


# =====================================================
# UPDATE REPORT
# =====================================================
@router.put("/{report_id}", response_model=ReportResponse)
def update_existing_report(
    report_id: int,
    report: ReportUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Update an existing report
    """
    return update_report(
        db=db,
        current_user=current_user,
        report_id=report_id,
        title=report.title,
        content=report.content.dict() if hasattr(report.content, "dict") else report.content,
    )


# =====================================================
# SOFT DELETE (MOVE TO TRASH)
# =====================================================
@router.delete("/{report_id}")
def delete_report(
    report_id: int,
    permanent: bool = Query(False, description="Permanently delete instead of soft delete"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),  # Changed to regular user
):
    """
    Move report to trash (soft delete)
    Regular users can soft delete their own reports
    """
    # Regular users can only soft delete
    if permanent and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required for permanent deletion")
    
    if permanent:
        return hard_delete_report(
            db=db,
            current_user=current_user,
            report_id=report_id,
        )
    else:
        return soft_delete_report(
            db=db,
            current_user=current_user,
            report_id=report_id,
        )


# =====================================================
# BULK DELETE REPORTS
# =====================================================
@router.post("/bulk-delete", response_model=BulkDeleteResponse)
def bulk_delete(
    request: BulkDeleteRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_required),  # Admin only
):
    """
    Bulk delete multiple reports (admin only)
    - Can soft delete or permanently delete
    """
    return bulk_delete_reports(
        db=db,
        current_user=current_user,
        report_ids=request.report_ids,
        permanent=request.permanent,
    )


# =====================================================
# RESTORE REPORT (FROM TRASH)
# =====================================================
@router.post("/{report_id}/restore")
def restore_deleted_report(
    report_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),  # Changed to regular user
):
    """
    Restore a report from trash
    Regular users can restore their own deleted reports
    """
    return restore_report(
        db=db,
        current_user=current_user,
        report_id=report_id,
    )


# =====================================================
# HARD DELETE (ADMIN ONLY)
# =====================================================
@router.delete("/{report_id}/hard")
def permanently_delete_report(
    report_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_required),
):
    """
    Permanently delete a report (admin only)
    """
    return hard_delete_report(
        db=db,
        current_user=current_user,
        report_id=report_id,
    )


# =====================================================
# EXPORT PDF
# =====================================================
@router.get("/{report_id}/export-pdf")
def export_pdf(
    report_id: int,
    watermark: bool = Query(False, description="Force watermark for preview"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Export report as premium PDF
    - Generates 15-21 page beautifully formatted PDF
    - Includes all sections: Executive Summary, Metrics, Archetype, Numerology, Planetary, etc.
    - Uses all assets: deities, mandala, logos, fonts
    
    Returns:
        StreamingResponse with PDF attachment
    """
    return export_report_pdf(
        db=db,
        current_user=current_user,
        report_id=report_id,
        watermark=watermark,
    )


# =====================================================
# PREVIEW PDF (FOR BASIC PLAN)
# =====================================================
@router.get("/{report_id}/preview-pdf")
def preview_pdf(
    report_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Preview report with watermark (for basic plan users)
    Same as export but forces watermark
    """
    return export_report_pdf(
        db=db,
        current_user=current_user,
        report_id=report_id,
        watermark=True,  # Force watermark for preview
    )


# =====================================================
# ADMIN: GET DELETED REPORTS
# =====================================================
@router.get("/admin/deleted", response_model=List[ReportResponse])
def get_deleted_reports(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_required),
):
    """
    Get all deleted reports (admin only)
    """
    return get_reports(
        db=db,
        current_user=current_user,
        skip=skip,
        limit=limit,
        include_deleted=True,
    )


# =====================================================
# ADMIN: EMPTY TRASH
# =====================================================
@router.delete("/admin/empty-trash")
def empty_trash(
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_required),
):
    """
    Permanently delete all soft-deleted reports (admin only)
    """
    deleted_reports = get_reports(
        db=db,
        current_user=current_user,
        skip=0,
        limit=1000,
        include_deleted=True,
    )
    
    report_ids = [
        r.get("id") if isinstance(r, dict) else r.id
        for r in deleted_reports
    ]
    report_ids = [report_id for report_id in report_ids if report_id is not None]
    
    if not report_ids:
        return {"message": "Trash is already empty"}
    
    return bulk_delete_reports(
        db=db,
        current_user=current_user,
        report_ids=report_ids,
        permanent=True,
    )

