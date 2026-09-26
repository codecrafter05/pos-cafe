from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.core.database import get_db
from app.models.sync_rejection import SyncRejection
from app.models.user import User
from app.schemas.sync import (
    SyncCatalogOut,
    SyncOrdersRequest,
    SyncOrdersResponse,
    SyncRejectionOut,
)
from app.services import sync_service

router = APIRouter(prefix="/sync", tags=["sync"])

_staff = require_roles("owner", "manager", "cashier")
_managers = require_roles("owner", "manager")


@router.get("/catalog", response_model=SyncCatalogOut)
def get_catalog(
    db: Session = Depends(get_db),
    _: User = Depends(_staff),
):
    return sync_service.get_device_catalog(db)


@router.post("/orders", response_model=SyncOrdersResponse)
def sync_orders(
    body: SyncOrdersRequest,
    db: Session = Depends(get_db),
    user: User = Depends(_staff),
):
    results = sync_service.sync_device_orders(
        db,
        user,
        body.orders,
        batch_device_id=body.device_id,
    )
    return SyncOrdersResponse(results=results)


@router.get("/rejections", response_model=list[SyncRejectionOut])
def list_rejections(
    db: Session = Depends(get_db),
    _: User = Depends(_managers),
    limit: int = Query(200, ge=1, le=500),
):
    rows = (
        db.query(SyncRejection)
        .order_by(SyncRejection.attempted_at.desc(), SyncRejection.id.desc())
        .limit(limit)
        .all()
    )
    return rows
