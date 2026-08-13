"""
등기부등본 OCR + HUG 악성임대인 명단 대조 라우터.

main.py에서는 아래처럼 include만 하면 됨:

    from app.ocr.router import router as ocr_router
    app.include_router(ocr_router, prefix="/register", tags=["ocr"])

이러면 최종 경로는 POST /register/check.
"""
from fastapi import APIRouter, UploadFile, File, HTTPException

from app.ocr import file_utils, ocr_engine, parser
from app.ocr.matcher import find_bad_landlord_matches
from app.ocr.schemas import (
    CurrentOwner,
    OcrRegisterResponse,
    OwnerMatchResult,
    RegisterCheckResponse,
)
router = APIRouter()

_STATUS_PRIORITY = {"MATCH_HIGH": 2, "MATCH_NAME_ONLY": 1, "NO_MATCH": 0}

@router.post("/ocr", response_model=OcrRegisterResponse)
async def ocr_register(files: list[UploadFile] = File(...)):
    filenames = [(f.filename or "").lower() for f in files]
    content_types = [(f.content_type or "").lower() for f in files]
    is_pdf_flags = [
        ct == "application/pdf" or fn.endswith(".pdf")
        for ct, fn in zip(content_types, filenames)
    ]
 
    if any(is_pdf_flags) and len(files) > 1:
        raise HTTPException(
            status_code=400,
            detail="PDF는 한 번에 1개만 업로드해주세요. (여러 장은 촬영 이미지에서만 지원)",
        )
 
    if is_pdf_flags and is_pdf_flags[0]:
        content = await files[0].read()
        if not content:
            raise HTTPException(status_code=400, detail="빈 파일입니다.")
 
        text = file_utils.extract_pdf_text(content)
        if text:
            source_type = "pdf_text"
        else:
            images = file_utils.pdf_to_images(content)
            text = ocr_engine.run_ocr_multi(images)
            source_type = "pdf_ocr"
    else:
        page_texts = []
        for f in files:
            content = await f.read()
            if not content:
                raise HTTPException(status_code=400, detail=f"{f.filename}이 빈 파일입니다.")
            try:
                img = file_utils.bytes_to_image(content)
            except ValueError as e:
                raise HTTPException(status_code=400, detail=f"{f.filename}: {e}")
 
            img = file_utils.preprocess_photo(img)
            page_texts.append(ocr_engine.run_ocr(img))
 
        text = "\n".join(page_texts)
        source_type = "image_ocr" if len(files) == 1 else "image_ocr_multi"
 
    if not text.strip():
        raise HTTPException(status_code=422, detail="텍스트를 추출하지 못했습니다.")
 
    fields = parser.parse_register_fields(text)
 
    return OcrRegisterResponse(
        current_owners=[CurrentOwner(**o) for o in fields["current_owners"]],
        ownership_history=fields["ownership_history"],
        has_cancellation_mention=fields["has_cancellation_mention"],
        raw_text=text,
        source_type=source_type,
    )


@router.post("/check", response_model=RegisterCheckResponse)
async def register_check(files: list[UploadFile] = File(...)):
    """
    등기부등본 업로드 -> OCR/파싱 -> 최종 소유자를 악성임대인 명단과 대조하는 엔드포인트
    """
    ocr_result = await ocr_register(files=files)
 
    results = []
    for owner in ocr_result.current_owners:
        match = find_bad_landlord_matches(
            name=owner.name,
            jumin_front=owner.jumin_front,
        )
        results.append(
            OwnerMatchResult(
                owner=owner,
                match_status=match.status,
                match_candidates=match.candidates,
            )
        )
 
    overall = "NO_MATCH"
    for r in results:
        if _STATUS_PRIORITY[r.match_status] > _STATUS_PRIORITY[overall]:
            overall = r.match_status
 
    return RegisterCheckResponse(
        owner_info=ocr_result,
        results=results,
        overall_match_status=overall,
    )
