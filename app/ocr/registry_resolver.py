import re

from app.ocr.registry_llm import RegistryLlmExtraction
from app.ocr.registry_locator import (
    RegistryTextLocator,
    address_is_supported,
    rank_is_supported,
    value_is_supported,
)
from app.ocr.registry_text_rules import (
    calc_age_from_jumin,
    classify_right_kind,
    split_registry_sections,
    target_rank_nos_from_purpose,
)


def _compact(value: str | None) -> str:
    return re.sub(r"\s+", "", value or "")


def _digits(value: str | int | None) -> str:
    return re.sub(r"\D", "", str(value or ""))


def _verified_value(value: str | None, locator: RegistryTextLocator) -> str | None:
    if value is None or locator.locate_value(value) is None:
        return None
    return value.strip()


def _to_int(value: str | None) -> int | None:
    if value is None:
        return None
    match = re.search(r"-?\d+", value.replace(",", ""))
    return int(match.group()) if match else None


def _to_float(value: str | None) -> float | None:
    if value is None:
        return None
    match = re.search(r"\d+(?:\.\d+)?", value.replace(",", ""))
    return float(match.group()) if match else None


def _normalise_date(value: str | None) -> str | None:
    if not value:
        return None
    match = re.search(
        r"(\d{4})\D+(\d{1,2})\D+(\d{1,2})",
        value,
    )
    if not match:
        return None
    return f"{match.group(1)}-{int(match.group(2)):02d}-{int(match.group(3)):02d}"


def _verified_share(share: str | None, page_text: str) -> str | None:
    if not share:
        return None
    slash = re.fullmatch(r"\s*(\d+)\s*/\s*(\d+)\s*", share)
    korean = re.fullmatch(r"\s*(\d+)\s*분의\s*(\d+)\s*", share)
    if slash:
        normalized = f"{slash.group(1)}/{slash.group(2)}"
        supported = value_is_supported(share, page_text) or (
            f"{slash.group(2)}분의{slash.group(1)}" in _compact(page_text)
        )
        return normalized if supported else None
    if korean and value_is_supported(share, page_text):
        return f"{korean.group(2)}/{korean.group(1)}"
    return share.strip() if value_is_supported(share, page_text) else None


def _unit_from_verified_address(address: str | None, suffix: str) -> str | None:
    if not address:
        return None
    match = re.search(rf"(?:제\s*)?([가-힣A-Za-z0-9-]+)\s*{suffix}\b", address)
    return match.group(1) if match else None


def _normalise_unit_label(value: str | None, suffix: str) -> str | None:
    if not value:
        return None
    normalized = value.strip()
    if normalized.startswith("제"):
        normalized = normalized[1:]
    if normalized.endswith(suffix):
        normalized = normalized[:-1]
    return normalized.strip() or None


def _property_address_from_header(text: str) -> str | None:
    match = re.search(
        r"^\s*[\[【]\s*(?:집합건물|건물|토지)\s*[\]】]\s*(.+?)\s*$",
        text,
        re.MULTILINE,
    )
    return match.group(1).strip() if match else None


def _issue_date_from_text(text: str) -> str | None:
    match = re.search(
        r"(?:열람|발급)일시\s*:\s*(\d{4})\s*년\s*(\d{1,2})\s*월\s*(\d{1,2})\s*일",
        text,
    )
    if not match:
        return None
    return f"{match.group(1)}-{int(match.group(2)):02d}-{int(match.group(3)):02d}"


def _normalise_owner(owner, locator: RegistryTextLocator) -> dict | None:
    located = locator.locate_owner(
        name=owner.name,
        jumin_front=owner.jumin_front,
        address=owner.address,
        share=owner.share,
    )
    if located is None or not owner.name:
        return None
    page_text = "\n".join(
        locator.page_texts[page - 1] for page in located.pages
    )
    jumin = (owner.jumin_front or "").strip()
    if jumin and _digits(jumin)[:6] not in _digits(page_text):
        jumin = ""
    address = (owner.address or "").strip()
    if address and not address_is_supported(address, page_text):
        address = ""
    return {
        "name": owner.name.strip(),
        "jumin_front": jumin,
        "address": address,
        "share": _verified_share(owner.share, page_text),
        "status": "CURRENT",
        "age": calc_age_from_jumin(jumin) if jumin else None,
    }


def _supported_optional(value: str | None, page_text: str) -> str | None:
    if not value:
        return None
    return value.strip() if value_is_supported(value, page_text) else None


def _resolve_rights(
    extraction: RegistryLlmExtraction,
    page_texts: tuple[str, ...],
    locator: RegistryTextLocator,
) -> dict:
    full_text = "\n".join(page_texts)
    sections = split_registry_sections(full_text)
    entries: list[dict] = []
    for item in extraction.rights:
        section_text = sections["gap" if item.section == "갑구" else "eul"]
        if section_text is None:
            continue
        target_candidates = list(dict.fromkeys((
            *item.target_rank_nos,
            *target_rank_nos_from_purpose(item.purpose),
        )))
        located = locator.locate_right(
            section_text=section_text,
            rank_no=item.rank_no,
            purpose=item.purpose,
            receipt_no=item.receipt_no,
            registered_at=item.registered_at,
            holder=item.holder,
            debtor=item.debtor,
            amount=item.amount,
            target_rank_nos=target_candidates,
            joint_collateral_id=item.joint_collateral_id,
        )
        if located is None:
            continue
        page_text = "\n".join(page_texts[page - 1] for page in located.pages)
        kind = classify_right_kind(item.purpose)
        target_rank_nos = [
            rank.strip()
            for rank in target_candidates
            if rank.strip() and locator.target_is_supported(rank, item.purpose, page_text)
        ]
        target_linked_kind = kind in {
            "CANCELLATION", "MORTGAGE_AMEND", "MORTGAGE_TRANSFER"
        }
        if not rank_is_supported(item.rank_no, page_text) and not (
            target_linked_kind and target_rank_nos
        ):
            continue
        entries.append({
            "section": item.section,
            "rank_no": item.rank_no.strip(),
            "kind": kind,
            "receipt_no": _supported_optional(item.receipt_no, page_text),
            "registered_at": _normalise_date(
                _supported_optional(item.registered_at, page_text)
            ),
            "holder": _supported_optional(item.holder, page_text),
            "debtor": _supported_optional(item.debtor, page_text),
            "amount": item.amount if item.amount is not None else None,
            "target_rank_nos": target_rank_nos,
            "joint_collateral_id": _supported_optional(item.joint_collateral_id, page_text),
            "raw_text": located.raw_text,
            "status": "ACTIVE",
        })

    cancelled = {
        (entry["section"], target)
        for entry in entries
        if entry["kind"] == "CANCELLATION"
        for target in entry["target_rank_nos"]
    }
    for entry in entries:
        if (entry["section"], entry["rank_no"]) in cancelled:
            entry["status"] = "CANCELLED"

    base_mortgages = [entry for entry in entries if entry["kind"] == "MORTGAGE"]
    mortgage_by_rank = {entry["rank_no"]: entry for entry in base_mortgages}
    mortgage_link_signatures = {
        entry["rank_no"]: set() for entry in base_mortgages
    }
    for amendment in entries:
        if amendment["kind"] != "MORTGAGE_AMEND":
            continue
        for target in amendment["target_rank_nos"]:
            mortgage = mortgage_by_rank.get(target)
            if mortgage is None:
                continue
            for field in ("amount", "holder", "debtor"):
                if amendment[field] is not None:
                    mortgage[field] = amendment[field]
            mortgage_link_signatures[target].add((
                amendment["registered_at"], amendment["receipt_no"], amendment["amount"]
            ))

    mortgages = [
        {
            "rank_no": entry["rank_no"],
            "receipt_no": entry["receipt_no"],
            "registered_at": entry["registered_at"],
            "creditor": entry["holder"],
            "debtor": entry["debtor"],
            "max_claim_amount": entry["amount"],
            "status": entry["status"],
        }
        for entry in base_mortgages
    ]

    active_mortgages = []
    seen_collateral: set[tuple[str, int | None]] = set()
    for entry in base_mortgages:
        if entry["status"] != "ACTIVE":
            continue
        collateral_id = entry["joint_collateral_id"]
        collateral_key = (collateral_id, entry["amount"]) if collateral_id else None
        if collateral_key and collateral_key in seen_collateral:
            continue
        if collateral_key:
            seen_collateral.add(collateral_key)
        active_mortgages.append(entry)

    def deposit_rights(kind: str) -> list[dict]:
        return [
            {
                "rank_no": entry["rank_no"],
                "receipt_no": entry["receipt_no"],
                "registered_at": entry["registered_at"],
                "holder": entry["holder"],
                "deposit_amount": entry["amount"],
                "status": entry["status"],
            }
            for entry in entries
            if entry["kind"] == kind
        ]

    jeonse_rights = deposit_rights("JEONSE_RIGHT")
    leaseholds = deposit_rights("LEASEHOLD_REGISTRATION")
    active_amounts = [entry["amount"] for entry in active_mortgages]
    total_mortgage = None if any(value is None for value in active_amounts) else sum(active_amounts)

    gap_entries = [entry for entry in entries if entry["section"] == "갑구"]
    eul_entries = [entry for entry in entries if entry["section"] == "을구"]
    gap_text = sections["gap"] or ""
    gap_has_risk_marker = any(
        marker in _compact(gap_text)
        for marker in ("압류", "가압류", "가처분", "경매개시결정", "신탁", "가등기")
    )
    eul_none = bool(
        sections["eul"] is not None
        and not eul_entries
        and re.search(r"기록\s*사항\s*없음", sections["eul"][:500])
    )
    gap_status = (
        "EXTRACTED"
        if sections["gap"] is not None and (gap_entries or not gap_has_risk_marker)
        else "PARSE_FAILED"
    )
    eul_status = (
        "CONFIRMED_NONE" if eul_none
        else "EXTRACTED" if eul_entries
        else "PARSE_FAILED"
    )

    flag_kinds = {
        "seizure": "SEIZURE",
        "provisional_seizure": "PROVISIONAL_SEIZURE",
        "provisional_disposition": "PROVISIONAL_DISPOSITION",
        "auction_commenced": "AUCTION",
        "trust_registration": "TRUST",
    }
    flags = {
        name: (
            "UNKNOWN" if gap_status == "PARSE_FAILED"
            else "TRUE" if any(
                entry["kind"] == kind and entry["status"] == "ACTIVE" for entry in entries
            ) else "FALSE"
        )
        for name, kind in flag_kinds.items()
    }
    flags["has_active_jeonse_right"] = (
        "UNKNOWN" if eul_status == "PARSE_FAILED"
        else "TRUE" if any(right["status"] == "ACTIVE" for right in jeonse_rights)
        else "FALSE"
    )
    flags["has_leasehold_registration"] = (
        "UNKNOWN" if eul_status == "PARSE_FAILED"
        else "TRUE" if any(right["status"] == "ACTIVE" for right in leaseholds)
        else "FALSE"
    )

    public_entries = [
        {key: value for key, value in entry.items() if key not in {
            "target_rank_nos", "joint_collateral_id"
        }}
        for entry in entries
    ]
    return {
        "gap_section_status": gap_status,
        "eul_section_status": eul_status,
        "rights": public_entries,
        "mortgages": mortgages,
        "jeonse_rights": jeonse_rights,
        "leasehold_registrations": leaseholds,
        "mortgage_link_signatures": {
            rank: sorted(signatures, key=str)
            for rank, signatures in mortgage_link_signatures.items()
        },
        "flags": flags,
        "active_mortgage_count": (
            len(active_mortgages) if eul_status != "PARSE_FAILED" else None
        ),
        "total_active_max_claim_amount": (
            total_mortgage if eul_status != "PARSE_FAILED" else None
        ),
        "llm_right_count": len(extraction.rights),
        "verified_right_count": len(entries),
    }


def resolve_registry_extraction(
    extraction: RegistryLlmExtraction,
    page_texts: tuple[str, ...],
) -> dict:
    locator = RegistryTextLocator(page_texts)
    full_text = "\n".join(page_texts)
    property_address = _verified_value(extraction.property_address, locator)
    if property_address is None:
        property_address = _property_address_from_header(full_text)
    issue_date = _verified_value(extraction.issue_date, locator)
    if issue_date is None:
        issue_date = _issue_date_from_text(full_text)
    issue_date = _normalise_date(issue_date)
    unit = extraction.unit
    current_owners = [
        owner for item in extraction.current_owners
        if (owner := _normalise_owner(item, locator)) is not None
    ]
    history = [
        owner for item in extraction.ownership_history
        if (owner := _normalise_owner(item, locator)) is not None
    ]
    rights = _resolve_rights(extraction, page_texts, locator)
    is_condominium = bool(re.search(r"[\[【]\s*집합건물\s*[\]】]", full_text))
    is_land = bool(re.search(r"[\[【]\s*토지\s*[\]】]", full_text))
    document_type = (
        "CONDOMINIUM" if is_condominium
        else "LAND" if is_land
        else "BUILDING"
    )
    if is_condominium:
        dong_name = _normalise_unit_label(
            _verified_value(unit.dong_name, locator), "동"
        ) or _unit_from_verified_address(property_address, "동")
        floor = _to_int(_verified_value(unit.floor, locator))
        if floor is None:
            floor = _to_int(_unit_from_verified_address(property_address, "층"))
        ho_name = _normalise_unit_label(
            _verified_value(unit.ho_name, locator), "호"
        ) or _unit_from_verified_address(property_address, "호")
        exclusive_area = _to_float(
            _verified_value(unit.exclusive_area_sqm, locator)
        )
    else:
        dong_name = None
        floor = None
        ho_name = None
        exclusive_area = None

    core_verified = bool(
        property_address
        and current_owners
        and len(current_owners) == len(extraction.current_owners)
        and all(owner["address"] for owner in current_owners)
        and (not is_condominium or exclusive_area is not None)
    )
    sections_verified = (
        rights["gap_section_status"] == "EXTRACTED"
        and rights["eul_section_status"] in {"EXTRACTED", "CONFIRMED_NONE"}
    )
    unresolved_mortgage = (
        rights["active_mortgage_count"] not in (None, 0)
        and rights["total_active_max_claim_amount"] is None
    )
    rights_complete = (
        rights["verified_right_count"] == rights["llm_right_count"]
    )
    if (
        not core_verified
        and rights["gap_section_status"] == "PARSE_FAILED"
        and rights["eul_section_status"] == "PARSE_FAILED"
    ):
        parse_status = "FAILED"
        parse_confidence = "UNKNOWN"
    elif not core_verified or not sections_verified:
        parse_status = "PARTIAL"
        parse_confidence = "LOW"
    elif unresolved_mortgage or not rights_complete:
        parse_status = "NEEDS_REVIEW"
        parse_confidence = "MEDIUM"
    else:
        parse_status = "SUCCESS"
        parse_confidence = "HIGH"

    return {
        "parse_status": parse_status,
        "parse_confidence": parse_confidence,
        "document_type": document_type,
        "property_address": property_address,
        "issue_date": issue_date,
        "dong_name": dong_name,
        "floor": floor,
        "ho_name": ho_name,
        "exclusive_area": exclusive_area,
        "current_owners": current_owners,
        "ownership_history": [
            {key: value for key, value in owner.items() if key in {"name", "jumin_front", "address"}}
            for owner in history
        ],
        "has_cancellation_mention": any(
            right["kind"] == "CANCELLATION" for right in rights["rights"]
        ),
        "has_joint_collateral_mention": "공동담보" in full_text,
        "registry_rights": rights,
    }
