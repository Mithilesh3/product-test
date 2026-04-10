# app/modules/reports/schemas.py

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime


# =====================================================
# BASIC REPORT CREATE (Manual Report)
# =====================================================

class ReportCreate(BaseModel):
    title: str
    content: Dict[str, Any]   # JSON-based storage


# =====================================================
# REPORT UPDATE
# =====================================================

class ReportUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[Dict[str, Any]] = None


# =====================================================
# REPORT RESPONSE (Enterprise Version)
# =====================================================

class ReportResponse(BaseModel):
    id: int
    title: str
    content: Dict[str, Any]
    engine_version: str
    confidence_score: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = {
        "from_attributes": True
    }


# =====================================================
# REPORT METRICS RESPONSE
# =====================================================

class ReportMetricsResponse(BaseModel):
    """
    Report usage metrics for dashboard
    """
    total_reports: int
    subscription_plan: str
    reports_used: int
    plan_limit: int
    reports_remaining: int
    # Backward-compatibility fields for older frontend builds.
    reports_used_this_month: Optional[int] = None
    monthly_limit: Optional[int] = None
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "total_reports": 15,
                "subscription_plan": "enterprise",
                "reports_used": 3,
                "plan_limit": 21,
                "reports_remaining": 18,
                "reports_used_this_month": 3,
                "monthly_limit": 21
            }
        }
    }


# =====================================================
# BULK DELETE REQUEST
# =====================================================

class BulkDeleteRequest(BaseModel):
    """
    Request model for bulk deleting reports
    """
    report_ids: List[int]
    permanent: bool = False
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "report_ids": [1, 2, 3, 4, 5],
                "permanent": False
            }
        }
    }


# =====================================================
# BULK DELETE RESPONSE
# =====================================================

class BulkDeleteResponse(BaseModel):
    """
    Response model for bulk delete operations
    """
    message: str
    processed_ids: List[int]
    not_found_ids: List[int]
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "message": "Successfully moved to trash 3 reports",
                "processed_ids": [1, 2, 3],
                "not_found_ids": [4, 5]
            }
        }
    }


# =====================================================
# RADAR DATA RESPONSE
# =====================================================

class RadarDataResponse(BaseModel):
    """
    Radar chart data points
    """
    Life_Stability: int
    Decision_Clarity: int
    Dharma_Alignment: int
    Emotional_Regulation: int
    Financial_Discipline: int
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "Life_Stability": 49,
                "Decision_Clarity": 83,
                "Dharma_Alignment": 47,
                "Emotional_Regulation": 46,
                "Financial_Discipline": 46
            }
        }
    }


# =====================================================
# REPORT FILTER PARAMS
# =====================================================

class ReportFilterParams(BaseModel):
    """
    Query parameters for filtering reports
    """
    skip: int = 0
    limit: int = 100
    include_deleted: bool = False
    from_date: Optional[datetime] = None
    to_date: Optional[datetime] = None
    min_confidence: Optional[int] = None
    max_confidence: Optional[int] = None


# =====================================================
# REPORT SUMMARY RESPONSE
# =====================================================

class ReportSummaryResponse(BaseModel):
    """
    Lightweight report summary for list views
    """
    id: int
    title: str
    confidence_score: int
    created_at: datetime
    is_deleted: bool = False
    plan_tier: Optional[str] = None
    
    model_config = {
        "from_attributes": True
    }


# =====================================================
# PDF EXPORT RESPONSE (for Swagger docs)
# =====================================================

class PDFExportResponse(BaseModel):
    """
    PDF export response (documentation only)
    Actual response is a binary PDF file
    """
    filename: str
    content_type: str = "application/pdf"
    size_bytes: Optional[int] = None
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "filename": "NumAI_Strategic_Brief_123_enterprise.pdf",
                "content_type": "application/pdf",
                "size_bytes": 524288
            }
        }
    }


# =====================================================
# ERROR RESPONSE
# =====================================================

class ErrorResponse(BaseModel):
    """
    Standard error response
    """
    detail: str
    error_code: Optional[str] = None
    timestamp: datetime = datetime.now()
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "detail": "Report limit reached",
                "error_code": "LIMIT_EXCEEDED",
                "timestamp": "2024-01-01T00:00:00Z"
            }
        }
    }


# =====================================================
# PLAN LIMITS RESPONSE
# =====================================================

class PlanLimitsResponse(BaseModel):
    """
    Plan limits information
    """
    plan_name: str
    plan_limit: int
    current_usage: int
    remaining: int
    is_active: bool
    expires_at: Optional[datetime] = None
    # Backward-compatibility field for older clients.
    monthly_limit: Optional[int] = None
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "plan_name": "enterprise",
                "plan_limit": 21,
                "current_usage": 3,
                "remaining": 18,
                "is_active": True,
                "expires_at": "2026-12-31T00:00:00Z",
                "monthly_limit": 21
            }
        }
    }
# =====================================================
# UNIQUENESS BENCHMARK (ADMIN DEBUG)
# =====================================================

class UniquenessBenchmarkRequest(BaseModel):
    user_count: int = Field(default=10, ge=2, le=30)
    target_difference: float = Field(default=0.90, ge=0.0, le=1.0)


class PlanUniquenessMetrics(BaseModel):
    plan: str
    users_tested: int
    sections_per_report: int
    pair_count: int
    sentence_jaccard_avg_difference: float
    sentence_jaccard_min_difference: float
    passes_target: bool


class UniquenessBenchmarkResponse(BaseModel):
    users_tested: int
    target_difference: float
    plans: Dict[str, PlanUniquenessMetrics]
    all_plans_pass_target: bool
