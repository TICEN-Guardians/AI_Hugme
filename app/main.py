import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.diagnosis.model.model_warmup import (
    ModelPrefetchStatus,
    get_model_prefetch_status,
    start_model_prefetch,
)
from app.diagnosis.router import router as diagnosis_router
from app.ocr.ocr_engine import load_engine
from app.ocr.router import router as ocr_router
from app.ocr_checklist.router import router as ocr_checklist_router


logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    load_engine()
    start_model_prefetch()
    yield


app = FastAPI(
    title="HUGME AI API",
    version="1.0.0",
    lifespan=lifespan,
)
app.include_router(
    ocr_checklist_router,
    prefix="/checklist",
    tags=["ocr-checklist"],
)
app.include_router(
    ocr_router,
    prefix="/register",
    tags=["ocr"],
)
app.include_router(diagnosis_router)


@app.get("/health")
async def health():
    prefetch_status = get_model_prefetch_status()
    service_status = {
        ModelPrefetchStatus.PENDING: "starting",
        ModelPrefetchStatus.READY: "ok",
        ModelPrefetchStatus.FAILED: "degraded",
        ModelPrefetchStatus.DISABLED: "ok",
    }[prefetch_status]

    return {
        "status": service_status,
        "diagnosisModels": {
            "prefetchStatus": prefetch_status.value,
            "ready": prefetch_status == ModelPrefetchStatus.READY,
        },
    }
