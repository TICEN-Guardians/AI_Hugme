import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException

from app.model_loader import load_model
from app.schemas import (
    PredictRequest,
    PredictResponse,
    BatchPredictRequest,
    BatchPredictResponse,
)
from app.inference import predict_one, predict_batch

logging.basicConfig(level=logging.INFO)

# 모델은 앱 상태(state)에 담아둔다
ml = {"model": None}


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 시작 시 1회: S3에서 가중치 받아 로드
    ml["model"] = load_model()
    yield
    # 종료 시 정리
    ml["model"] = None


app = FastAPI(title="Regression Inference API", version="1.0.0", lifespan=lifespan)


@app.get("/health")
async def health():
    return {"status": "ok", "model_loaded": ml["model"] is not None}


@app.post("/predict", response_model=PredictResponse)
async def predict(req: PredictRequest):
    if ml["model"] is None:
        raise HTTPException(status_code=503, detail="model not loaded")
    try:
        value = predict_one(ml["model"], req.features)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    return PredictResponse(prediction=value)


@app.post("/predict/batch", response_model=BatchPredictResponse)
async def predict_batch_endpoint(req: BatchPredictRequest):
    if ml["model"] is None:
        raise HTTPException(status_code=503, detail="model not loaded")
    try:
        values = predict_batch(ml["model"], req.instances)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    return BatchPredictResponse(predictions=values)
