import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api.v1.router import router
from app.api.v1.endpoints.web import router as web_router

TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "..", "template")


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(
    title="Pod Café POS",
    version="1.0.0",
    description="Single-tenant coffee shop point-of-sale backend.",
    lifespan=lifespan,
)

# Serve template assets at /assets and /sass
app.mount("/assets", StaticFiles(directory=os.path.join(TEMPLATE_DIR, "assets")), name="assets")
app.mount("/sass", StaticFiles(directory=os.path.join(TEMPLATE_DIR, "sass")), name="sass")

# API routes
app.include_router(router)

# Web (HTML) routes — must come after static mounts
app.include_router(web_router)
