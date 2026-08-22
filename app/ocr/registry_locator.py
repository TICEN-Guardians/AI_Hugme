from dataclasses import dataclass
import re


def canonical(value: str | None) -> str:
    return re.sub(r"[^0-9A-Za-z가-힣]", "", value or "").lower()


def digits(value: str | int | None) -> str:
    return re.sub(r"\D", "", str(value or ""))


def value_is_supported(value: str | int | None, text: str) -> bool:
    raw_value = str(value or "")
    value_text = canonical(raw_value)
    source_text = canonical(text)
    if value_text and value_text in source_text:
        return True

    numeric_only = isinstance(value, int) or bool(
        re.fullmatch(r"[0-9\s,./:()\-]+", raw_value)
    )
    value_digits = digits(value)
    if not numeric_only or len(value_digits) < 2:
        return False
    separator = r"[\s,./:()\-년월일]*"
    pattern = separator.join(re.escape(number) for number in value_digits)
    return bool(re.search(pattern, text))


def purpose_is_supported(purpose: str, text: str) -> bool:
    if value_is_supported(purpose, text):
        return True
    compact_purpose = canonical(purpose)
    compact_text = canonical(text)
    required = []
    for marker in (
        "근저당권", "전세권", "임차권", "압류", "가압류", "가처분",
        "경매개시결정", "신탁", "가등기", "말소", "변경", "이전",
    ):
        if marker in compact_purpose:
            required.append(marker)
    target = re.match(r"(\d+(?:-\d+)?)번", compact_purpose)
    if target:
        required.append(f"{target.group(1)}번")
    return bool(required) and all(canonical(token) in compact_text for token in required)


def rank_is_supported(rank_no: str, text: str) -> bool:
    normalized = re.sub(r"\s*번\s*$", "", rank_no.strip())
    if not normalized:
        return False
    composite = re.fullmatch(r"(\d+)\((\d+)\)", normalized)
    if composite:
        pattern = re.compile(
            rf"(?m)^[ \t]*{composite.group(1)}[ \t]*$\r?\n"
            rf"[ \t]*\({composite.group(2)}\)"
        )
        return bool(pattern.search(text))
    pattern = re.compile(
        rf"(?m)^\s*{re.escape(normalized)}(?=\s|$)"
    )
    return bool(pattern.search(text))


def address_is_supported(address: str, text: str) -> bool:
    if value_is_supported(address, text):
        return True
    address_tokens = re.findall(r"[가-힣A-Za-z]+|\d+", address)
    source_tokens = re.findall(r"[가-힣A-Za-z]+|\d+", text)
    if len(address_tokens) < 3:
        return False
    source_index = 0
    for token in address_tokens:
        token_text = canonical(token)
        while source_index < len(source_tokens):
            if canonical(source_tokens[source_index]) == token_text:
                source_index += 1
                break
            source_index += 1
        else:
            return False
    return True


@dataclass(frozen=True)
class LocatedEvidence:
    pages: tuple[int, ...]
    raw_text: str


class RegistryTextLocator:
    def __init__(self, page_texts: tuple[str, ...]):
        self.page_texts = page_texts
        self._canonical_pages = tuple(canonical(text) for text in page_texts)

    def locate_value(self, value: str | int | None) -> LocatedEvidence | None:
        if value is None or not str(value).strip():
            return None
        for page, page_text in enumerate(self.page_texts, start=1):
            if value_is_supported(value, page_text):
                return LocatedEvidence((page,), self._source_excerpt(page_text, [str(value)]))
        return None

    def locate_owner(
        self,
        *,
        name: str | None,
        jumin_front: str | None,
        address: str | None,
        share: str | None,
    ) -> LocatedEvidence | None:
        if not name:
            return None
        for page, page_text in enumerate(self.page_texts, start=1):
            compact_page = self._canonical_pages[page - 1]
            compact_name = canonical(name)
            start = 0
            while compact_name and (position := compact_page.find(compact_name, start)) >= 0:
                window = compact_page[max(0, position - 700):position + len(compact_name) + 700]
                identity_supported = (
                    not jumin_front or value_is_supported(jumin_front, window)
                )
                evidence_pages = (page,)
                address_source = page_text
                address_supported = (
                    not address or address_is_supported(address, address_source)
                )
                if identity_supported and not address_supported and page < len(self.page_texts):
                    evidence_pages = (page, page + 1)
                    address_source = page_text + "\n" + self.page_texts[page]
                    address_supported = address_is_supported(address, address_source)
                if identity_supported and address_supported:
                    source_values = [name, jumin_front, address, share]
                    excerpts = []
                    for evidence_page in evidence_pages:
                        excerpt = self._source_excerpt(
                            self.page_texts[evidence_page - 1],
                            [value for value in source_values if value],
                        )
                        if excerpt:
                            excerpts.append(f"[PAGE {evidence_page}] {excerpt}")
                    return LocatedEvidence(evidence_pages, " ".join(excerpts))
                start = position + len(compact_name)
        return None

    def locate_right(
        self,
        *,
        section_text: str,
        rank_no: str,
        purpose: str,
        receipt_no: str | None,
        registered_at: str | None,
        holder: str | None,
        debtor: str | None,
        amount: int | None,
        target_rank_nos: list[str],
        joint_collateral_id: str | None,
    ) -> LocatedEvidence | None:
        if not purpose or not purpose_is_supported(purpose, section_text):
            return None
        receipt_supported = bool(
            receipt_no and value_is_supported(receipt_no, section_text)
        )
        target_anchors = [
            f"{target}번 {purpose}"
            for target in target_rank_nos
            if not canonical(purpose).startswith(f"{canonical(target)}번")
        ]
        anchored_pages = [
            page
            for page, page_text in enumerate(self.page_texts, start=1)
            if any(value_is_supported(anchor, page_text) for anchor in target_anchors)
        ]
        exact_pages = [
            page
            for page, page_text in enumerate(self.page_texts, start=1)
            if value_is_supported(purpose, page_text)
        ]
        semantic_pages = [
            page
            for page, page_text in enumerate(self.page_texts, start=1)
            if purpose_is_supported(purpose, page_text)
        ]
        purpose_pages = anchored_pages or exact_pages or semantic_pages
        if not purpose_pages:
            cross_page_purpose_pages: set[int] = set()
            for first_page in range(1, len(self.page_texts)):
                source_text = (
                    self.page_texts[first_page - 1]
                    + "\n"
                    + self.page_texts[first_page]
                )
                if purpose_is_supported(purpose, source_text):
                    cross_page_purpose_pages.update((first_page, first_page + 1))
            purpose_pages = sorted(cross_page_purpose_pages)
        if not purpose_pages:
            return None
        candidate_groups: set[tuple[int, ...]] = set()
        if receipt_supported:
            receipt_pages = [
                page
                for page, page_text in enumerate(self.page_texts, start=1)
                if value_is_supported(receipt_no, page_text)
            ]
            for receipt_page in receipt_pages:
                for purpose_page in purpose_pages:
                    if abs(receipt_page - purpose_page) <= 1:
                        first, last = sorted((receipt_page, purpose_page))
                        candidate_groups.add(tuple(range(first, last + 1)))
        else:
            for page in purpose_pages:
                candidate_groups.add((page,))
                if page > 1:
                    candidate_groups.add((page - 1, page))
                if page < len(self.page_texts):
                    candidate_groups.add((page, page + 1))
        if not candidate_groups:
            return None

        scored: list[tuple[int, tuple[int, ...]]] = []
        for pages in candidate_groups:
            source_text = "\n".join(self.page_texts[page - 1] for page in pages)
            if not purpose_is_supported(purpose, source_text):
                continue
            score = 10 if receipt_supported else 4
            checks = [registered_at, holder, debtor, amount, joint_collateral_id]
            score += 2 if rank_is_supported(rank_no, source_text) else 0
            score += sum(1 for value in checks if value and value_is_supported(value, source_text))
            score += sum(
                1 for target in target_rank_nos
                if self.target_is_supported(target, purpose, source_text)
            )
            if amount is not None and not value_is_supported(amount, source_text):
                continue
            scored.append((score, pages))
        if not scored:
            return None

        best_quality = max((score, -len(pages)) for score, pages in scored)
        best_groups = sorted(
            pages
            for score, pages in scored
            if (score, -len(pages)) == best_quality
        )
        if len(best_groups) != 1:
            return None
        pages = best_groups[0]
        values = [
            purpose, receipt_no, rank_no, registered_at, holder, debtor,
            str(amount) if amount is not None else None, joint_collateral_id,
            *target_rank_nos,
        ]
        excerpts = []
        for page in pages:
            excerpt = self._source_excerpt(
                self.page_texts[page - 1],
                [value for value in values if value],
            )
            if excerpt:
                excerpts.append(f"[PAGE {page}] {excerpt}")
        return LocatedEvidence(pages, " ".join(excerpts))

    @staticmethod
    def target_is_supported(target: str, purpose: str, page_text: str) -> bool:
        target_compact = canonical(target)
        if not target_compact:
            return False
        purpose_compact = canonical(purpose)
        if f"{target_compact}번" in purpose_compact:
            return True
        target_pattern = re.compile(rf"(?<!\d){re.escape(target)}\s*번")
        return bool(target_pattern.search(page_text)) and purpose_is_supported(purpose, page_text)

    @staticmethod
    def _source_excerpt(page_text: str, values: list[str]) -> str:
        lines = [line.strip() for line in page_text.splitlines() if line.strip()]
        matched_indexes: set[int] = set()
        for value in values:
            value_text = canonical(value)
            value_digits = digits(value)
            for index, line in enumerate(lines):
                line_text = canonical(line)
                if (
                    value_text and value_text in line_text
                    or len(value_digits) >= 2 and value_digits in digits(line)
                ):
                    matched_indexes.update(range(max(0, index - 1), min(len(lines), index + 2)))
                    break
        if not matched_indexes:
            return ""
        return " | ".join(lines[index] for index in sorted(matched_indexes))
