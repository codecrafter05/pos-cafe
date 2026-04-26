from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.core.database import check_db_connection

router = APIRouter(tags=["health"])


@router.get("/health")
def health():
    return {"status": "ok"}


@router.get("/db-check")
def db_check():
    ok = check_db_connection()
    if ok:
        return {"status": "ok", "database": "connected"}
    return JSONResponse(
        status_code=503,
        content={"status": "error", "database": "unreachable"},
    )
