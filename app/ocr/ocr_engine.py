"""
RapidOCR 래퍼 - 앱 시작 시 1회만 모델 로드

최초 실행 시 한국어 인식 모델(korean_PP-OCRv4_rec_mobile.onnx, 약 10~15MB)을
ModelScope CDN(modelscope.cn)에서 자동 다운로드.
미리 모델을 받아 로컬 경로로 지정하는 방향도 고려.
"""
import numpy as np
from rapidocr import RapidOCR, LangRec, OCRVersion, ModelType

_engine: RapidOCR | None = None

def load_engine() -> RapidOCR:
    """앱 시작 시(lifespan) 1회만 호출. 여기서 모델 로드/다운로드가 실제로 일어남."""
    global _engine
    _engine = RapidOCR(
        params={
            "Rec.lang_type": LangRec.KOREAN,
            "Rec.ocr_version": OCRVersion.PPOCRV4,
            "Rec.model_type": ModelType.MOBILE,
        }
    )
    return _engine

def get_engine() -> RapidOCR:
    """이미 로드된 엔진을 반환."""
    if _engine is None:
        raise RuntimeError(
            "OCR 엔진이 아직 로드되지 않았습니다."
        )
    return _engine


def run_ocr(img: np.ndarray) -> str:
    """이미지 1장에서 텍스트를 추출해 줄 단위로 이어붙인 문자열 반환."""
    engine = get_engine()
    result = engine(img)
    if not result or not result.txts:
        return ""
    return "\n".join(result.txts)


def run_ocr_multi(images: list[np.ndarray]) -> str:
    """여러 페이지 이미지를 순서대로 OCR 후 합침."""
    texts = [run_ocr(img) for img in images]
    return "\n".join(texts)
