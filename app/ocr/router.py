"""
등기부등본 OCR + HUG 악성임대인 명단 대조 라우터.

main.py에서는 아래처럼 include만 하면 됨:

    from app.ocr.router import router as ocr_router
    app.include_router(ocr_router, prefix="/register", tags=["ocr"])
"""
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, UploadFile, File, Form, HTTPException

from app.ocr import file_utils, ocr_engine, parser
from app.ocr.matcher import find_bad_landlord_matches
from app.ocr.registry_repository import save_registry_result, save_watchlist_checks
from app.ocr.schemas import (
    CurrentOwner,
    OcrRegisterResponse,
    OwnerMatchResult,
    RegisterCheckResponse,
    RegistrySummary,
)

router = APIRouter()
logger = logging.getLogger(__name__)

_STATUS_PRIORITY = {"MATCH_HIGH": 3, "MATCH_NAME_ONLY": 2, "UNKNOWN": 1, "NO_MATCH": 0}


@router.post("/ocr", response_model=OcrRegisterResponse)
async def ocr_register(
    files: list[UploadFile] = File(...),
    analysis_id: str = Form(...),
):
    if not files:
        raise HTTPException(status_code=400, detail="파일이 없습니다.")

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

    ocr_confidence: float | None = None  # pdf_text 경로는 OCR 자체가 없어서 None 유지

    if is_pdf_flags and is_pdf_flags[0]:
        content = await files[0].read()
        if not content:
            raise HTTPException(status_code=400, detail="빈 파일입니다.")

        text = file_utils.extract_pdf_text(content)
        if text:
            source_type = "pdf_text"
        else:
            images = file_utils.pdf_to_images(content)
            text, ocr_confidence = ocr_engine.run_ocr_multi(images)
            source_type = "pdf_ocr"
    else:
        page_texts = []
        page_confidences = []
        for f in files:
            content = await f.read()
            if not content:
                raise HTTPException(status_code=400, detail=f"{f.filename}이 빈 파일입니다.")
            try:
                img = file_utils.bytes_to_image(content)
            except ValueError as e:
                raise HTTPException(status_code=400, detail=f"{f.filename}: {e}")

            img = file_utils.preprocess_photo(img)
            page_text, page_conf = ocr_engine.run_ocr(img)
            page_texts.append(page_text)
            if page_conf is not None:
                page_confidences.append(page_conf)

        text = "\n".join(page_texts)
        ocr_confidence = (
            sum(page_confidences) / len(page_confidences) if page_confidences else None
        )
        source_type = "image_ocr" if len(files) == 1 else "image_ocr_multi"

    if not text.strip():
        raise HTTPException(status_code=422, detail="텍스트를 추출하지 못했습니다.")

    if source_type == "pdf_text":
        parse_confidence = "HIGH"
    elif ocr_confidence is None:
        parse_confidence = "UNKNOWN"
    elif ocr_confidence >= 0.9:
        parse_confidence = "HIGH"
    elif ocr_confidence >= 0.7:
        parse_confidence = "MEDIUM"
    else:
        parse_confidence = "LOW"

    fields = parser.parse_register_fields(text)
    rights = fields["registry_rights"]

    return OcrRegisterResponse(
        analysis_id=analysis_id,
        parse_status=fields["parse_status"],
        parse_confidence=parse_confidence,
        parsed_at=datetime.now(timezone.utc).isoformat(),
        raw_address=fields["property_address"],
        property_address=fields["property_address"],
        dong_name=fields["dong_name"],
        floor=fields["floor"],
        ho_name=fields["ho_name"],
        exclusive_area=fields["exclusive_area"],
        issue_date=fields["issue_date"],
        current_owners=[CurrentOwner(**o) for o in fields["current_owners"]],
        ownership_history=fields["ownership_history"],
        rights=rights["rights"],
        mortgages=rights["mortgages"],
        jeonse_rights=rights["jeonse_rights"],
        leasehold_registrations=rights["leasehold_registrations"],
        summary=RegistrySummary(
            gap_section_status=rights["gap_section_status"],
            eul_section_status=rights["eul_section_status"],
            active_mortgage_count=rights["active_mortgage_count"],
            total_active_max_claim_amount=rights["total_active_max_claim_amount"],
            **{
                ("has_active_leasehold_registration" if k == "has_leasehold_registration" else k): v
                for k, v in rights["flags"].items()
            },
        ),
        has_cancellation_mention=fields["has_cancellation_mention"],
        raw_text=text,
        source_type=source_type,
    )


@router.post("/check", response_model=RegisterCheckResponse)
async def register_check(
    files: list[UploadFile] = File(...),
    analysis_id: str = Form(...),
):
    """
    등기부등본 업로드 -> OCR/파싱(권리 포함) -> 최종 소유자(들)를 bad_landlord 명단과
    대조까지 한 번에 처리. 위험도 진단 흐름에서 실제로 쓰는 엔드포인트.
    """
    ocr_result = await ocr_register(files=files, analysis_id=analysis_id)

    results = []

    if not ocr_result.current_owners:
        # 등본 파싱 실패 등으로 소유자를 하나도 못 뽑은 경우
        results.append(
            OwnerMatchResult(
                owner=None,
                check_status="NOT_CHECKED",
                matched=None,
                match_type=None,
                match_status="UNKNOWN",
                match_candidates=[],
                checked_at=datetime.now(timezone.utc).isoformat(),
            )
        )

    for owner in ocr_result.current_owners:
        checked_at = datetime.now(timezone.utc).isoformat()
        try:
            match = find_bad_landlord_matches(
                name=owner.name,
                jumin_front=owner.jumin_front,
            )
            status = match.status
            candidates = match.candidates
            check_status = "CHECKED"
        except Exception:
            logger.exception(
                "악성임대인 조회 실패 (analysis_id=%s)",
                analysis_id,
            )
            status = "UNKNOWN"
            candidates = []
            check_status = "ERROR"

        matched: bool | None
        match_type: str | None
        if status == "MATCH_HIGH":
            matched, match_type = True, "EXACT"
        elif status == "MATCH_NAME_ONLY":
            matched, match_type = None, "MANUAL_REVIEW"
        elif status == "NO_MATCH":
            matched, match_type = False, None
        else:  # UNKNOWN
            matched, match_type = None, None

        results.append(
            OwnerMatchResult(
                owner=owner,
                check_status=check_status,
                matched=matched,
                match_type=match_type,
                match_status=status,
                match_candidates=candidates,
                checked_at=checked_at,
            )
        )

    overall = "UNKNOWN" if not ocr_result.current_owners else "NO_MATCH"
    for r in results:
        if _STATUS_PRIORITY.get(r.match_status, 0) > _STATUS_PRIORITY[overall]:
            overall = r.match_status

    response = RegisterCheckResponse(
        owner_info=ocr_result,
        results=results,
        overall_match_status=overall,
    )

    # DB 저장
    # 저장에 실패하면 위험도 진단이 등기 권리관계를 통째로 빠뜨린 채 수행되므로
    # 성공으로 응답하지 않는다.
    try:
        registry_result_id, owner_ids = save_registry_result(analysis_id, ocr_result)
        save_watchlist_checks(analysis_id, registry_result_id, owner_ids, response)
    except Exception as e:
        logger.exception("registry 저장 실패 (analysis_id=%s): %s", analysis_id, e)
        raise HTTPException(
            status_code=500,
            detail="등기부등본 분석 결과를 저장하지 못했습니다. 다시 시도해 주세요.",
        ) from e

    return response
