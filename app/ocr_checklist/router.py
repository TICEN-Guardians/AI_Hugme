"""개인정보를 마스킹한 계약서 이미지 LLM 체크리스트 라우터."""

from fastapi import APIRouter, File, HTTPException, UploadFile
from starlette.concurrency import run_in_threadpool

from app.ocr import ocr_engine
from . import file_utils, llm_parser
from .schemas import OcrChecklistResponse


router = APIRouter()
TOP_OCR_MIN_WIDTH = 1400
TOP_OCR_MAX_SCALE = 1.5


@router.post("/ocr", response_model=OcrChecklistResponse)
async def ocr_checklist(
    files: list[UploadFile] = File(...),
):
    """상단 OCR 텍스트와 마스킹된 하단 이미지를 LLM으로 분석한다."""
    if len(files) != 1:
        raise HTTPException(
            status_code=400,
            detail="한 페이지가 담긴 이미지 파일을 정확히 1장 보내주세요.",
        )

    image = await read_one_image(files[0])

    prepared = file_utils.deskew_document(image)

    top_third, _ = file_utils.split_top_third_bottom_two_thirds(prepared)
    top_ocr_input = file_utils.upscale_small_document(
        top_third,
        min_width=TOP_OCR_MIN_WIDTH,
        max_scale=TOP_OCR_MAX_SCALE,
    )
    masked_full_image = file_utils.mask_sensitive_party_fields(prepared)
    _, masked_bottom = file_utils.split_top_third_bottom_two_thirds(
        masked_full_image
    )
    masked_image_bytes = file_utils.image_to_jpeg_bytes(masked_bottom)

    try:
        top_ocr_text, _ = await run_in_threadpool(
            ocr_engine.run_ocr,
            top_ocr_input,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    if not top_ocr_text.strip():
        raise HTTPException(
            status_code=422,
            detail="계약서 위쪽 영역에서 OCR 텍스트를 추출하지 못했습니다.",
        )

    try:
        fields = await llm_parser.extract_fields_from_hybrid_input(
            top_ocr_text=top_ocr_text,
            image_bytes=masked_image_bytes,
            media_type="image/jpeg",
        )
    except RuntimeError as exc:
        status_code = 503 if "OPENAI_API_KEY" in str(exc) else 502
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"OCR 텍스트·마스킹 이미지 LLM 분석에 실패했습니다: {exc}",
        ) from exc

    # contractAddress는 판독 불가 시 null을 허용하고, 나머지는 누락되거나
    # null이면 OcrChecklistResponse에 선언된 기본값을 사용한다.
    response_fields = {
        key: value
        for key, value in (fields or {}).items()
        if value is not None or key == "contractAddress"
    }
    return OcrChecklistResponse.model_validate(response_fields)


async def read_one_image(file: UploadFile):
    """업로드된 한 페이지 이미지를 BGR로 디코딩한다."""
    is_pdf = (
        (file.content_type or "").lower() == "application/pdf"
        or (file.filename or "").lower().endswith(".pdf")
    )
    if is_pdf:
        raise HTTPException(
            status_code=400,
            detail="한 페이지 이미지 1장만 지원합니다.",
        )

    content = await file.read()
    if not content:
        raise HTTPException(
            status_code=400,
            detail=f"{file.filename or 'image'}이 빈 파일입니다.",
        )

    try:
        return file_utils.bytes_to_image(content)
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(
            status_code=400,
            detail=f"{file.filename}: {exc}",
        ) from exc
