"""
파일 타입 분기 및 전처리 유틸
- PDF: 텍스트 레이어 우선 추출 시도, 없으면 이미지로 렌더링 후 OCR
- JPG/PNG: 촬영 이미지 전처리(기울기 보정, 대비 향상) 후 OCR
"""
import io
import numpy as np
import cv2
import fitz  # pymupdf


def extract_pdf_text(pdf_bytes: bytes) -> str:
    """PDF에 텍스트 레이어가 있으면 바로 추출. 없으면 빈 문자열 반환."""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    text_parts = []
    for page in doc:
        text_parts.append(page.get_text())
    doc.close()
    return "\n".join(text_parts).strip()


def pdf_to_images(pdf_bytes: bytes, dpi: int = 300) -> list[np.ndarray]:
    """스캔본 PDF를 페이지별 이미지(numpy array, BGR)로 렌더링."""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    images = []
    zoom = dpi / 72  # PDF 기본 해상도 72dpi 기준 배율
    matrix = fitz.Matrix(zoom, zoom)
    for page in doc:
        pix = page.get_pixmap(matrix=matrix)
        img_bytes = pix.tobytes("png")
        img_array = np.frombuffer(img_bytes, dtype=np.uint8)
        img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
        images.append(img)
    doc.close()
    return images


def bytes_to_image(image_bytes: bytes) -> np.ndarray:
    img_array = np.frombuffer(image_bytes, dtype=np.uint8)
    img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("이미지를 디코딩할 수 없습니다.")
    return img


def preprocess_photo(img: np.ndarray) -> np.ndarray:
    """
    오프라인 서류 촬영 이미지 전처리:
    1) 그레이스케일 변환
    2) 기울기 보정(deskew)
    3) 대비 향상(CLAHE)
    """
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # --- 기울기 보정 ---
    gray = _deskew(gray)

    # --- 대비 향상 (조명 불균일한 촬영본에 효과적) ---
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)

    # RapidOCR은 BGR 3채널 입력을 기대하므로 다시 변환
    result = cv2.cvtColor(enhanced, cv2.COLOR_GRAY2BGR)
    return result


def _deskew(gray: np.ndarray) -> np.ndarray:
    """이진화 후 텍스트 영역의 최소 외접 사각형 각도로 기울기 보정."""
    thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)[1]
    coords = np.column_stack(np.where(thresh > 0))

    if coords.shape[0] < 50:
        # 텍스트 픽셀이 너무 적으면 보정 스킵
        return gray

    angle = cv2.minAreaRect(coords)[-1]
    if angle < -45:
        angle = -(90 + angle)
    else:
        angle = -angle

    # 실제 촬영 문서는 보통 ±15도 이내로 기울어짐.
    # 이 범위를 벗어나면 minAreaRect가 텍스트 블록 형태(여러 줄 문단 등) 때문에
    # 각도를 잘못 계산했을 가능성이 높으므로 보정을 스킵한다 (안전장치).
    MAX_CORRECTION_DEG = 15.0
    if abs(angle) < 0.3 or abs(angle) > MAX_CORRECTION_DEG:
        return gray

    (h, w) = gray.shape[:2]
    center = (w // 2, h // 2)
    matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
    rotated = cv2.warpAffine(
        gray, matrix, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE
    )
    return rotated
