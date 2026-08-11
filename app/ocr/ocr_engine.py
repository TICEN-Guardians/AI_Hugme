"""
RapidOCR 래퍼 - 앱 시작 시 1회만 모델 로드 (요청마다 로드하면 느림)

주의: rapidocr_onnxruntime(구버전)이 아니라 신형 통합 패키지 rapidocr>=3.9 사용.
기본 모델은 중국어/영어 기준이라 한글 인식이 거의 안 되므로,
반드시 Rec.lang_type=KOREAN 설정 필요.

최초 실행 시 한국어 인식 모델(korean_PP-OCRv4_rec_mobile.onnx, 약 10~15MB)을
ModelScope CDN(modelscope.cn)에서 자동 다운로드함. 사내망/방화벽 환경이면
이 도메인 접근이 막혀 있을 수 있으니, 그런 경우 사내 프록시를 통하거나
미리 모델을 받아 로컬 경로로 지정해야 함 (RapidOCR(params={"Rec.model_path": "..."}))
"""
import numpy as np
from rapidocr import RapidOCR, LangRec, OCRVersion, ModelType

_engine: RapidOCR | None = None


def get_engine() -> RapidOCR:
    global _engine
    if _engine is None:
        _engine = RapidOCR(
            params={
                "Rec.lang_type": LangRec.KOREAN,
                "Rec.ocr_version": OCRVersion.PPOCRV4,
                "Rec.model_type": ModelType.MOBILE,
            }
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
