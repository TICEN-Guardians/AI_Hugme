"""체크리스트 이미지 디코딩, 회전 보정, OCR 전처리 유틸."""

import cv2
import numpy as np


SENSITIVE_PARTY_MASK_RATIO = (0.16, 0.68, 0.54, 0.96)


def mask_sensitive_party_fields(image: np.ndarray) -> np.ndarray:
    """당사자 표의 주소·주민등록번호·전화번호 열을 넓게 검정 처리한다.

    현재 지원하는 한 페이지 계약서 양식을 기준으로 한 상대 좌표다. 오른쪽의
    성명·도장 열은 개인/법인 및 공동명의·대리인 판독을 위해 남긴다.
    """
    masked = image.copy()
    height, width = masked.shape[:2]
    left, top, right, bottom = SENSITIVE_PARTY_MASK_RATIO
    x1, y1 = round(width * left), round(height * top)
    x2, y2 = round(width * right), round(height * bottom)
    cv2.rectangle(masked, (x1, y1), (x2, y2), (0, 0, 0), thickness=-1)
    return masked


def image_to_jpeg_bytes(image: np.ndarray, quality: int = 95) -> bytes:
    """BGR 이미지를 OpenAI 이미지 입력용 JPEG bytes로 인코딩한다."""
    encoded_ok, encoded = cv2.imencode(
        ".jpg",
        image,
        [cv2.IMWRITE_JPEG_QUALITY, quality],
    )
    if not encoded_ok:
        raise ValueError("마스킹한 이미지를 JPEG로 인코딩할 수 없습니다.")
    return encoded.tobytes()


def bytes_to_image(image_bytes: bytes) -> np.ndarray:
    """업로드된 이미지 bytes를 BGR 이미지로 디코딩한다."""
    data = np.frombuffer(image_bytes, dtype=np.uint8)
    image = cv2.imdecode(data, cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError("이미지를 디코딩할 수 없습니다.")
    return image


def upscale_small_document(
    image: np.ndarray,
    min_width: int = 1200,
    max_scale: float = 3.0,
) -> np.ndarray:
    """작은 문서만 확대한다. 큰 이미지는 원본 해상도를 유지한다."""
    height, width = image.shape[:2]
    if width >= min_width:
        return image.copy()

    scale = min(min_width / width, max_scale)
    return cv2.resize(
        image,
        (round(width * scale), round(height * scale)),
        interpolation=cv2.INTER_CUBIC,
    )


def deskew_document(image: np.ndarray) -> np.ndarray:
    """Otsu 결과로 각도를 계산하고 컬러 원본에 회전 보정을 적용한다."""
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    binary = cv2.threshold(
        gray,
        0,
        255,
        cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU,
    )[1]
    coords = np.column_stack(np.where(binary > 0))

    if coords.shape[0] < 50:
        return image.copy()

    angle = cv2.minAreaRect(coords)[-1]
    angle = -(90 + angle) if angle < -45 else -angle

    if abs(angle) < 0.3 or abs(angle) > 15:
        return image.copy()

    height, width = image.shape[:2]
    matrix = cv2.getRotationMatrix2D(
        (width // 2, height // 2),
        angle,
        1.0,
    )
    return cv2.warpAffine(
        image,
        matrix,
        (width, height),
        flags=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_REPLICATE,
    )


def split_top_third_bottom_two_thirds(
    image: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """페이지를 위쪽 1/3과 아래쪽 2/3으로 분리한다."""
    height = image.shape[0]
    if height < 3:
        raise ValueError("이미지 높이가 너무 작아 3등분할 수 없습니다.")
    split_y = height // 3
    return image[:split_y, :].copy(), image[split_y:, :].copy()


def crop_horizontal_half(
    image: np.ndarray,
    *,
    half: str,
) -> np.ndarray:
    """이미지를 가로선으로 나눠 위쪽 또는 아래쪽 절반을 반환한다."""
    height = image.shape[0]
    if height < 2:
        raise ValueError("이미지 높이가 너무 작아 절반으로 나눌 수 없습니다.")

    middle = height // 2
    if half == "top":
        return image[:middle, :].copy()
    if half == "bottom":
        return image[middle:, :].copy()
    raise ValueError("half는 top 또는 bottom이어야 합니다.")


def stack_top_quarter_bottom_half(image: np.ndarray) -> np.ndarray:
    """페이지의 위쪽 1/4과 아래쪽 1/2을 세로로 이어 붙인다."""
    height = image.shape[0]
    if height < 4:
        raise ValueError("이미지 높이가 너무 작아 선택 영역을 자를 수 없습니다.")

    top = image[:height // 4, :]
    bottom = image[height // 2:, :]
    return np.vstack((top, bottom)).copy()


def preprocess_ocr_crop_stages(image: np.ndarray) -> dict[str, np.ndarray]:
    """잘라낸 영역의 OCR 전처리 단계별 이미지를 반환한다."""
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    enhanced = cv2.createCLAHE(
        clipLimit=2.0,
        tileGridSize=(8, 8),
    ).apply(gray)
    bgr = cv2.cvtColor(enhanced, cv2.COLOR_GRAY2BGR)
    return {
        "grayscale": gray,
        "clahe": enhanced,
        "bgr": bgr,
    }
