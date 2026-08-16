from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.core.database import get_db
from app.models.user import User
from app.schemas.sync import SyncCatalogOut, SyncOrdersRequest, SyncOrdersResponse
from app.services import sync_service

router = APIRouter(prefix="/sync", tags=["sync"])

_staff = require_roles("owner", "manager", "cashier")


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
