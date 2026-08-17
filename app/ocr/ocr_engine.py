"""
RapidOCR 래퍼 - 앱 시작 시 1회만 모델 로드

최초 실행 시 한국어 인식 모델(korean_PP-OCRv4_rec_mobile.onnx, 약 10~15MB)을
ModelScope CDN(modelscope.cn)에서 자동 다운로드.
미리 모델을 받았다면 해당 로컬 모델 사용.
"""
import numpy as np
from rapidocr import RapidOCR, LangRec, OCRVersion, ModelType

import os
from pathlib import Path

_engine: RapidOCR | None = None

_DET_FILENAME = "PP-OCRv6_det_small.onnx"
_REC_FILENAME = "korean_PP-OCRv4_rec_mobile.onnx"

def _resolve_model_path(env_key: str, default_filename: str) -> Path:
    """
    DET_MODEL_PATH/REC_MODEL_PATH가 명시돼있으면 그걸 최우선으로,
    없으면 OCR_MODELS_DIR(기본 /tmp/ocr_models) + 파일명으로 조립.
    """
    explicit = os.environ.get(env_key)
    if explicit:
        return Path(explicit)
 
    models_dir = Path(os.environ.get("OCR_MODELS_DIR", "/tmp/ocr_models"))
    return models_dir / default_filename

def load_engine() -> RapidOCR:
    """앱 시작 시(lifespan) 1회만 호출. 여기서 모델 로드/다운로드가 실제로 일어남."""
    global _engine
    
    params = {
        "Rec.lang_type": LangRec.KOREAN,
        "Rec.ocr_version": OCRVersion.PPOCRV4,
        "Rec.model_type": ModelType.MOBILE,
    }

    det_path = _resolve_model_path("DET_MODEL_PATH", _DET_FILENAME)
    rec_path = _resolve_model_path("REC_MODEL_PATH", _REC_FILENAME)
    if det_path.is_file():
        params["Det.model_path"] = str(det_path)
    if rec_path.is_file():
        params["Rec.model_path"] = str(rec_path)

    _engine = RapidOCR(params=params)
    return _engine

def get_engine() -> RapidOCR:
    """로드된 엔진을 반환."""
    if _engine is None:
        raise RuntimeError(
            "OCR 엔진이 아직 로드되지 않았습니다."
        )
    return _engine


def run_ocr(img: np.ndarray) -> tuple[str, float | None]:
    """이미지 1장에서 텍스트를 추출해 줄 단위로 이어붙인 문자열 반환."""
    engine = get_engine()
    result = engine(img)
    if not result or not result.txts:
        return "", None
    text = "\n".join(result.txts)
    scores = [s for s in (result.scores or []) if s is not None]
    confidence = sum(scores) / len(scores) if scores else None
    return text, confidence


def run_ocr_multi(images: list[np.ndarray]) -> tuple[str, float | None]:
    """여러 페이지 이미지를 순서대로 OCR 후 합침."""
    pages = [run_ocr(img) for img in images]
    text = "\n".join(t for t, _ in pages)
    confidences = [c for _, c in pages if c is not None]
    confidence = sum(confidences) / len(confidences) if confidences else None
    return text, confidence
