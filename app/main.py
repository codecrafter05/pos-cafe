from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles

from app.api.v1.router import router
from app.api.v1.endpoints.web import router as web_router
from app.api.store import router as store_router
from app.core.paths import PRODUCT_UPLOAD_DIR, STATIC_DIR, TEMPLATE_DIR


@asynccontextmanager
async def lifespan(app: FastAPI):
    PRODUCT_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    yield


app = FastAPI(
    title="Pod Café POS",
    version="1.0.0",
    description="Single-tenant coffee shop point-of-sale backend.",
    lifespan=lifespan,
)


@app.middleware("http")
async def no_store_api(request: Request, call_next):
    response = await call_next(request)
    if request.url.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
        response.headers["Pragma"] = "no-cache"
    return response


# Serve template assets at /assets and /sass
app.mount("/assets", StaticFiles(directory=str(TEMPLATE_DIR / "assets")), name="assets")
app.mount("/sass", StaticFiles(directory=str(TEMPLATE_DIR / "sass")), name="sass")
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

app.include_router(store_router, prefix="/api/store")

# API routes (v1)
app.include_router(router)

# Web (HTML) routes — must come after static mounts
app.include_router(web_router)
