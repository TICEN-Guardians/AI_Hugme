"""주택임대차계약서 한 페이지 OCR + LLM 체크리스트 라우터."""

from fastapi import APIRouter, File, HTTPException, UploadFile
from starlette.concurrency import run_in_threadpool

from app.ocr import ocr_engine
from . import file_utils, llm_parser
from .schemas import OcrChecklistResponse


router = APIRouter()

OCR_CROP_MIN_WIDTH = 1800
OCR_CROP_MAX_SCALE = 2.0


@router.post("/ocr", response_model=OcrChecklistResponse)
async def ocr_checklist(
    files: list[UploadFile] = File(...),
):
    """한 이미지를 위·아래 절반으로 나눠 OCR한 뒤 항상 LLM으로 분석한다."""
    if len(files) != 1:
        raise HTTPException(
            status_code=400,
            detail="한 페이지가 담긴 이미지 파일을 정확히 1장 보내주세요.",
        )

    image = await read_one_image(files[0])
    prepared = file_utils.deskew_document(image)

    crop_specs = ("top", "bottom")
    ocr_texts: list[str] = []

    for half in crop_specs:
        cropped = file_utils.crop_horizontal_half(
            prepared,
            half=half,
        )
        upscaled = file_utils.upscale_small_document(
            cropped,
            min_width=OCR_CROP_MIN_WIDTH,
            max_scale=OCR_CROP_MAX_SCALE,
        )
        stages = file_utils.preprocess_ocr_crop_stages(upscaled)
        ocr_input = stages["bgr"]

        try:
            text = await run_in_threadpool(ocr_engine.run_ocr, ocr_input)
        except RuntimeError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        ocr_texts.append(text)

    if not any(text.strip() for text in ocr_texts):
        raise HTTPException(
            status_code=422,
            detail="두 영역에서 OCR 텍스트를 추출하지 못했습니다.",
        )

    try:
        fields = await llm_parser.extract_fields_from_ocr_text(
            top_half_text=ocr_texts[0],
            bottom_half_text=ocr_texts[1],
        )
    except RuntimeError as exc:
        status_code = 503 if "OPENAI_API_KEY" in str(exc) else 502
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"OCR 텍스트 LLM 분석에 실패했습니다: {exc}",
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
