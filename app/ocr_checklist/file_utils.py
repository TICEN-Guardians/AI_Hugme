"""체크리스트 이미지 디코딩, 회전 보정, OCR 전처리 유틸."""

import cv2
import numpy as np




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


