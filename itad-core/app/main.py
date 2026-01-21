from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.bol import router as bol_router
from app.api.v1.processing import router as processing_router
from app.api.v1.pickup_manifests import router as pickup_manifests_router
from app.api.v1.receiving import router as receiving_router
from app.api.v1.taxonomy import router as taxonomy_router
from app.api.v1.workstreams import router as workstreams_router
from app.api.v1.material_types import router as material_types_router
from app.core.config import settings
from app.core.db import create_tables
from app.core.correlation import CorrelationMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await create_tables()
    yield
    # Shutdown


app = FastAPI(
    title="ITAD Core API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(CorrelationMiddleware)

app.include_router(bol_router, prefix="/api/v1", tags=["BOL"])
app.include_router(pickup_manifests_router, prefix="/api/v1", tags=["PickupManifests"])
app.include_router(receiving_router, prefix="/api/v1", tags=["Receiving"])
app.include_router(workstreams_router, prefix="/api/v1", tags=["Workstreams"])
app.include_router(taxonomy_router, prefix="/api/v1", tags=["Taxonomy"])
app.include_router(processing_router, prefix="/api/v1", tags=["Processing"])
app.include_router(material_types_router, prefix="/api/v1", tags=["MaterialTypes"])


@app.get("/healthz")
async def health_check():
    return {"status": "ok"}
