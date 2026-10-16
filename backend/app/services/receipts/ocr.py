"""Tesseract OCR wrapper with light preprocessing.

Requires the Tesseract binary. Locally set TESSERACT_CMD if it is not on PATH
(on Windows the default install path is detected automatically). In AWS the
receipt Lambda runs as a container image that includes Tesseract.
"""

from __future__ import annotations

import io
import os
import shutil
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageFilter, ImageOps

from app.errors import ServiceUnavailable, ValidationFailed

WINDOWS_DEFAULT = Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe")


@dataclass
class OcrLine:
    text: str
    confidence: float  # 0-100, mean word confidence


@dataclass
class OcrResult:
    lines: list[OcrLine]
    mean_confidence: float

    @property
    def text(self) -> str:
        return "\n".join(line.text for line in self.lines)


def resolve_tesseract(cmd: str | None) -> str | None:
    if cmd and Path(cmd).exists():
        return cmd
    found = shutil.which("tesseract")
    if found:
        return found
    if os.name == "nt" and WINDOWS_DEFAULT.exists():
        return str(WINDOWS_DEFAULT)
    return None


def tesseract_available(cmd: str | None) -> bool:
    return resolve_tesseract(cmd) is not None


def preprocess(data: bytes) -> Image.Image:
    with Image.open(io.BytesIO(data)) as raw:
        img = ImageOps.exif_transpose(raw)
        img = img.convert("L")
    # Upscale small images: Tesseract works best with ~300 DPI text.
    if img.width < 1000:
        factor = 1000 / img.width
        img = img.resize((int(img.width * factor), int(img.height * factor)), Image.Resampling.LANCZOS)
    elif img.width > 2500:
        factor = 2500 / img.width
        img = img.resize((int(img.width * factor), int(img.height * factor)), Image.Resampling.LANCZOS)
    img = ImageOps.autocontrast(img, cutoff=1)
    img = img.filter(ImageFilter.SHARPEN)
    return img


def run_ocr(data: bytes, tesseract_cmd: str | None = None, timeout: int = 30) -> OcrResult:
    import pytesseract

    cmd = resolve_tesseract(tesseract_cmd)
    if not cmd:
        raise ServiceUnavailable("OCR engine (Tesseract) is not installed on the server.", code="ocr_unavailable")
    pytesseract.pytesseract.tesseract_cmd = cmd
    image = preprocess(data)
    try:
        # psm 4: assume a single column of text of variable sizes (typical receipt).
        raw = pytesseract.image_to_data(image, config="--oem 3 --psm 4", output_type=pytesseract.Output.DICT,
                                        timeout=timeout)
    except RuntimeError as exc:  # timeout
        raise ValidationFailed("OCR timed out. Try a smaller or clearer image.", code="ocr_timeout") from exc
    except pytesseract.TesseractError as exc:
        raise ValidationFailed("The image could not be processed by OCR.", code="ocr_failed") from exc

    grouped: dict[tuple[int, int, int], list[tuple[str, float]]] = {}
    order: list[tuple[int, int, int]] = []
    for i, word in enumerate(raw["text"]):
        word = (word or "").strip()
        conf = float(raw["conf"][i])
        if not word or conf < 0:
            continue
        key = (raw["block_num"][i], raw["par_num"][i], raw["line_num"][i])
        if key not in grouped:
            grouped[key] = []
            order.append(key)
        grouped[key].append((word, conf))

    lines = []
    for key in order:
        words = grouped[key]
        lines.append(OcrLine(text=" ".join(w for w, _ in words),
                             confidence=round(sum(c for _, c in words) / len(words), 1)))
    all_conf = [c for words in grouped.values() for _, c in words]
    mean = round(sum(all_conf) / len(all_conf), 1) if all_conf else 0.0
    return OcrResult(lines=lines, mean_confidence=mean)
