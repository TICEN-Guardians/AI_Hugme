import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException

from app.inference import predict_batch, predict_one
from app.model_loader import load_model
from app.schemas import (
    BatchPredictRequest,
    BatchPredictResponse,
    PredictRequest,
    PredictResponse,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("hugme-ai")

# Model은 Application 실행 중 메모리에 보관한다.
ml = {"model": None}


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 현재는 실제 전세·매매 시세추정 Model이 아직 준비되지 않았으므로
    # Model Load에 실패하더라도 FastAPI Application 자체는 실행한다.
    try:
        ml["model"] = load_model()
        logger.info("Model load completed.")
    except Exception:
        ml["model"] = None
        logger.warning(
            "Model is not available yet. FastAPI starts without a model."
        )

    yield

    # Application 종료 시 Model 참조를 정리한다.
    ml["model"] = None


app = FastAPI(
    title="HUGME AI API",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "model_loaded": ml["model"] is not None,
    }


@app.post("/predict", response_model=PredictResponse)
async def predict(req: PredictRequest):
    if ml["model"] is None:
        raise HTTPException(
            status_code=503,
            detail="model not loaded",
        )

    try:
        value = predict_one(ml["model"], req.features)
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=str(e),
        )

    return PredictResponse(prediction=value)


@app.post("/predict/batch", response_model=BatchPredictResponse)
async def predict_batch_endpoint(req: BatchPredictRequest):
    if ml["model"] is None:
        raise HTTPException(
            status_code=503,
            detail="model not loaded",
        )

    try:
        values = predict_batch(ml["model"], req.instances)
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=str(e),
        )

    return BatchPredictResponse(predictions=values)