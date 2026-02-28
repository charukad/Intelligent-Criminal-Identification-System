from typing import Any, Dict
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select, func

from src.infrastructure.database import get_db
from src.api.deps import get_current_user
from src.domain.models.user import User
from src.domain.models.criminal import Criminal, ThreatLevel
from src.domain.models.case import Case, CaseStatus
from src.domain.models.audit import AuditLog
from datetime import datetime, timedelta

router = APIRouter()

@router.get("/", response_model=Dict[str, Any])
async def get_dashboard_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Get statistics for the frontend dashboard.
    """
    # Count total criminals
    criminals_query = select(func.count(Criminal.id))
    criminals_result = await db.execute(criminals_query)
    total_criminals = criminals_result.scalar() or 0
    
    # Count critical threats
    critical_query = select(func.count(Criminal.id)).where(Criminal.threat_level == ThreatLevel.CRITICAL)
    critical_result = await db.execute(critical_query)
    critical_alerts = critical_result.scalar() or 0
    
    # Count open/active cases
    cases_query = select(func.count(Case.id)).where(
        Case.status.in_([CaseStatus.OPEN, CaseStatus.UNDER_INVESTIGATION])
    )
    cases_result = await db.execute(cases_query)
    active_cases = cases_result.scalar() or 0
    
    # Query recent identifications
    time_threshold = datetime.utcnow() - timedelta(hours=24)
    identifications_query = select(func.count(AuditLog.id)).where(
        AuditLog.action == "IDENTIFY",
        AuditLog.timestamp >= time_threshold
    )
    ident_result = await db.execute(identifications_query)
    recent_identifications = ident_result.scalar() or 0
    
    return {
        "totalCriminals": total_criminals,
        "criticalAlerts": critical_alerts,
        "recentIdentifications": recent_identifications,
        "activeInvestigations": active_cases
    }
