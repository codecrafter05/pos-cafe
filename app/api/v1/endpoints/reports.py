from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.core.database import get_db
from app.models.user import User
from app.schemas.dashboard import ReportSummaryOut
from app.services import dashboard_service

router = APIRouter(prefix="/reports", tags=["reports"])

_admin = require_roles("owner", "manager")


@router.get("/summary", response_model=ReportSummaryOut)
def report_summary(
    date_from: Annotated[date, Query()],
    date_to: Annotated[date, Query()],
    db: Session = Depends(get_db),
    _: User = Depends(_admin),
):
    if date_to < date_from:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="date_to must be on or after date_from",
        )
    if (date_to - date_from).days > 366:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Range cannot exceed 366 days",
        )
    return ReportSummaryOut(**dashboard_service.report_for_range(db, date_from=date_from, date_to=date_to))
