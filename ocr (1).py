"""
ocr.py — OCR + Document Classification (Keshav's scope)

Pipeline: file (PDF/image) -> raw text extraction -> per-region confidence
-> document classification (invoice / contract / other).

This module owns exactly what 07_plan_keshav.md and TRD §2.1 assign to Keshav:
OCR + classification. It does NOT do field extraction (that's the LLM call
in llm.py) and does NOT do validation/comparison.

Engine strategy:
- Native-text PDFs: extract text directly via pypdf (fast, perfect confidence,
  no OCR needed at all).
- Scanned PDFs / images: PaddleOCR (primary). Falls back to Tesseract
  automatically if PaddleOCR isn't installed/working, so the rest of the
  pipeline never hard-crashes on an environment where the heavy PaddleOCR
  install didn't go cleanly (see 07_plan_keshav.md Day 0 note).
"""

import os
import io
from typing import Optional

# ---------------------------------------------------------------------------
# Lazy-loaded engines. We don't want `import ocr` to eagerly load PaddleOCR
# models (slow, ~several seconds) on every FastAPI cold start / test run
# that doesn't actually need OCR (e.g. native-text PDFs).
# ---------------------------------------------------------------------------

_paddle_ocr_instance = None
_paddle_available: Optional[bool] = None  # None = not checked yet

_tesseract_available: Optional[bool] = None


def _get_paddle_ocr():
    """Lazily construct a singleton PaddleOCR instance. Returns None if
    PaddleOCR isn't importable/usable, so callers can fall back cleanly."""
    global _paddle_ocr_instance, _paddle_available

    if _paddle_available is False:
        return None
    if _paddle_ocr_instance is not None:
        return _paddle_ocr_instance

    try:
        from paddleocr import PaddleOCR
        _paddle_ocr_instance = PaddleOCR(use_angle_cls=True, lang="en", show_log=False)
        _paddle_available = True
        return _paddle_ocr_instance
    except Exception as e:
        print(f"[ocr.py] PaddleOCR unavailable ({e}); will fall back to Tesseract.")
        _paddle_available = False
        return None


def _tesseract_ready() -> bool:
    global _tesseract_available
    if _tesseract_available is not None:
        return _tesseract_available
    try:
        import pytesseract  # noqa: F401
        _tesseract_available = True
    except Exception as e:
        print(f"[ocr.py] Tesseract unavailable ({e}).")
        _tesseract_available = False
    return _tesseract_available


# ---------------------------------------------------------------------------
# Step 1 (of 07_plan_keshav.md) — raw OCR pass
# ---------------------------------------------------------------------------

def _ocr_image_paddle(image_path: str) -> dict:
    """Run PaddleOCR on a single image. Returns raw text + per-line
    confidence + bounding boxes, matching the plan's Step 1 output shape."""
    ocr = _get_paddle_ocr()
    result = ocr.ocr(image_path, cls=True)

    lines = []
    # PaddleOCR wraps results per-image: result = [[ [box, (text, conf)], ... ]]
    page = result[0] if result and result[0] is not None else []
    for entry in page:
        box, (text, conf) = entry
        lines.append({"text": text, "confidence": float(conf), "box": box})

    full_text = "\n".join(l["text"] for l in lines)
    avg_conf = sum(l["confidence"] for l in lines) / len(lines) if lines else 0.0

    return {
        "engine": "paddleocr",
        "text": full_text,
        "avg_confidence": avg_conf,
        "lines": lines,
        "low_confidence_lines": [l for l in lines if l["confidence"] < 0.75],
    }


def _ocr_image_tesseract(image_path: str) -> dict:
    """Fallback engine. Confidence is normalized to PaddleOCR's 0-1 scale
    (Tesseract natively reports 0-100) so downstream status logic (Step 4)
    doesn't need to know which engine ran."""
    import pytesseract
    from pytesseract import Output

    data = pytesseract.image_to_data(image_path, output_type=Output.DICT)
    lines = []
    for text, conf in zip(data["text"], data["conf"]):
        text = text.strip()
        conf = float(conf)
        if not text or conf < 0:
            continue
        lines.append({"text": text, "confidence": conf / 100.0, "box": None})

    full_text = " ".join(l["text"] for l in lines)
    avg_conf = sum(l["confidence"] for l in lines) / len(lines) if lines else 0.0

    return {
        "engine": "tesseract",
        "text": full_text,
        "avg_confidence": avg_conf,
        "lines": lines,
        "low_confidence_lines": [l for l in lines if l["confidence"] < 0.75],
    }


def ocr_image(image_path: str) -> dict:
    """Run OCR on a single image file, PaddleOCR first, Tesseract fallback.
    Never raises — an unreadable image comes back as a zero-confidence
    empty result rather than crashing the pipeline (TRD §5 "no silent
    failure" / "failure isolation")."""
    if _get_paddle_ocr() is not None:
        try:
            return _ocr_image_paddle(image_path)
        except Exception as e:
            print(f"[ocr.py] PaddleOCR failed on {image_path}: {e}; trying Tesseract.")

    if _tesseract_ready():
        try:
            return _ocr_image_tesseract(image_path)
        except Exception as e:
            print(f"[ocr.py] Tesseract failed on {image_path}: {e}")

    return {
        "engine": "none",
        "text": "",
        "avg_confidence": 0.0,
        "lines": [],
        "low_confidence_lines": [],
        "error": "No OCR engine available or OCR failed on this file.",
    }


def _pdf_has_text_layer(pdf_path: str) -> str:
    """Return extracted text if the PDF is digital-native (has a real text
    layer), else empty string. Native text is always full-confidence and
    skips OCR entirely — cheaper and more accurate."""
    try:
        from pypdf import PdfReader
        reader = PdfReader(pdf_path)
        text = "\n".join((page.extract_text() or "") for page in reader.pages)
        return text.strip()
    except Exception as e:
        print(f"[ocr.py] pypdf text-layer check failed on {pdf_path}: {e}")
        return ""


def _pdf_to_images(pdf_path: str) -> list:
    from pdf2image import convert_from_path
    return convert_from_path(pdf_path)


def ocr_pdf(pdf_path: str) -> dict:
    """PDF entry point. Tries the native text layer first (Step 1 shortcut);
    only rasterizes + OCRs pages that have no text layer (scanned/photographed
    PDFs, per TRD §2.1 "must handle native PDF text, scanned/photographed")."""
    native_text = _pdf_has_text_layer(pdf_path)
    if native_text:
        return {
            "engine": "native_pdf_text",
            "text": native_text,
            "avg_confidence": 1.0,
            "lines": [],
            "low_confidence_lines": [],
        }

    # No text layer -> scanned PDF -> rasterize pages and OCR each
    try:
        images = _pdf_to_images(pdf_path)
    except Exception as e:
        return {
            "engine": "none",
            "text": "",
            "avg_confidence": 0.0,
            "lines": [],
            "low_confidence_lines": [],
            "error": f"Could not rasterize PDF ({e}). Is poppler installed?",
        }

    combined_text = []
    all_lines = []
    confidences = []
    tmp_dir = "/tmp/aegis_ocr_pages"
    os.makedirs(tmp_dir, exist_ok=True)

    for i, img in enumerate(images):
        page_path = os.path.join(tmp_dir, f"{os.path.basename(pdf_path)}_p{i}.png")
        img.save(page_path, "PNG")
        page_result = ocr_image(page_path)
        combined_text.append(page_result["text"])
        all_lines.extend(page_result["lines"])
        if page_result["avg_confidence"]:
            confidences.append(page_result["avg_confidence"])

    return {
        "engine": "paddleocr_rasterized" if _paddle_available else "tesseract_rasterized",
        "text": "\n".join(combined_text),
        "avg_confidence": sum(confidences) / len(confidences) if confidences else 0.0,
        "lines": all_lines,
        "low_confidence_lines": [l for l in all_lines if l["confidence"] < 0.75],
    }


def run_ocr(file_path: str) -> dict:
    """Single entry point for any supported file. Dispatches by extension."""
    ext = os.path.splitext(file_path)[1].lower()
    if ext == ".pdf":
        return ocr_pdf(file_path)
    elif ext in (".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif", ".webp"):
        return ocr_image(file_path)
    else:
        return {
            "engine": "none",
            "text": "",
            "avg_confidence": 0.0,
            "lines": [],
            "low_confidence_lines": [],
            "error": f"Unsupported file type: {ext}",
        }


# ---------------------------------------------------------------------------
# Step 2 — document classification (keyword heuristic, per the plan)
# ---------------------------------------------------------------------------

INVOICE_SIGNALS = [
    "invoice number", "invoice no", "invoice #", "total due", "bill to",
    "amount due", "gst number", "gstin", "tax invoice", "remit to",
    "purchase order", "subtotal", "invoice date",
]

CONTRACT_SIGNALS = [
    "party of the first part", "party of the second part", "hereby agrees",
    "terms and conditions", "witnesseth", "this agreement", "governing law",
    "in witness whereof", "shall indemnify", "effective date", "termination clause",
]


def classify_document(text: str) -> str:
    """Simple keyword-signal classifier per 07_plan_keshav.md Step 2.
    Returns 'invoice', 'contract', or 'other'. Ties go to whichever has
    more signal hits; genuine ties fall back to 'other' rather than a
    guess (TRD §5 — no silent, unjustified guess)."""
    lowered = text.lower()
    invoice_hits = sum(1 for s in INVOICE_SIGNALS if s in lowered)
    contract_hits = sum(1 for s in CONTRACT_SIGNALS if s in lowered)

    if invoice_hits == 0 and contract_hits == 0:
        return "other"
    if invoice_hits > contract_hits:
        return "invoice"
    if contract_hits > invoice_hits:
        return "contract"
    return "other"


# ---------------------------------------------------------------------------
# Combined entry point used by main.py's /upload
# ---------------------------------------------------------------------------

def process_document(file_path: str) -> dict:
    """OCR + classification in one call. This is what /upload should invoke.
    Field extraction (LLM step) happens downstream in /extract — not here."""
    ocr_result = run_ocr(file_path)
    doc_type = classify_document(ocr_result["text"])
    return {
        "ocr_text": ocr_result["text"],
        "document_type": doc_type,
        "ocr_engine": ocr_result["engine"],
        "avg_confidence": ocr_result["avg_confidence"],
        "low_confidence_regions": ocr_result.get("low_confidence_lines", []),
        "error": ocr_result.get("error"),
    }
