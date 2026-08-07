"""
Brochure masking pipeline — phones/contact info blurred & color-matched.
Output filename is exactly the same as input filename (no 'masked_' prefix).
"""

import os
import json
import tempfile
import logging
import time
import re
import shutil
from typing import Optional

import fitz  # PyMuPDF
import numpy as np
import cv2
from PIL import Image
from google import genai
from google.genai import types

Image.MAX_IMAGE_PIXELS = None
logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────────────
# HELPER FUNCTIONS
# ──────────────────────────────────────────────────────────────────────────────

def get_dominant_color(
    image: Image.Image,
    x1: int, y1: int, x2: int, y2: int,
    width: int, height: int,
    sample_margin: int = 10,
) -> tuple:
    """Finds the dominant color in the area *around* a bounding box using numpy mean."""
    try:
        sx1 = max(0, x1 - sample_margin)
        sy1 = max(0, y1 - sample_margin)
        sx2 = min(width, x2 + sample_margin)
        sy2 = min(height, y2 + sample_margin)

        if sx1 >= sx2 or sy1 >= sy2:
            return (255, 255, 255, 255)

        sample = image.crop((sx1, sy1, sx2, sy2)).convert("RGB")
        pixels = np.array(sample).reshape(-1, 3)
        if pixels.shape[0] == 0:
            return (255, 255, 255, 255)

        c = pixels.mean(axis=0).astype(int)
        return (int(c[0]), int(c[1]), int(c[2]), 255)
    except Exception:
        return (255, 255, 255, 255)


def _clean_json_str(text: str) -> str:
    """Clean markdown backticks from JSON responses."""
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```$", "", text)
    return text.strip()


def _upload_and_wait(client: genai.Client, file_path: str, mime_type: str = None):
    """Upload a file to Gemini and poll until ACTIVE."""
    uf = client.files.upload(
        file=file_path,
        config={"mime_type": mime_type} if mime_type else None,
    )
    while uf.state.name == "PROCESSING":
        time.sleep(3)
        uf = client.files.get(name=uf.name)
    if uf.state.name == "FAILED":
        raise ValueError("Gemini file processing failed.")
    return uf


# ──────────────────────────────────────────────────────────────────────────────
# MAIN PIPELINE
# ──────────────────────────────────────────────────────────────────────────────

def mask_brochure(
    pdf_path: str,
    api_key: str,
    output_dir: str = "Masked",
    output_filename: Optional[str] = None,
    progress_callback=None,
) -> dict:
    """
    Full masking pipeline for a single PDF.

    Args:
        pdf_path:         Path to the input PDF.
        api_key:          Gemini API key.
        output_dir:       Directory to save the masked PDF.
        output_filename:  Final filename for the output (e.g. 'XID.pdf').
                          If None, uses the original filename.
        progress_callback: Optional callable(msg: str) for live logging.

    Returns:
        dict with keys: status (bool), data (output path | None), reason (str)
    """
    response = {"status": False, "data": None, "reason": ""}
    client = genai.Client(api_key=api_key)
    model_name = "gemini-3-flash-preview"

    def _log(msg: str):
        logger.info(msg)
        if progress_callback:
            progress_callback(msg)

    try:
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF not found: {pdf_path}")

        final_filename = output_filename or os.path.basename(pdf_path)
        if not final_filename.lower().endswith(".pdf"):
            final_filename += ".pdf"

        # ── STEP 1: Find contact pages ──────────────────────────────────────
        _log("Uploading PDF to Gemini for contact-page detection…")
        uploaded_pdf = _upload_and_wait(client, pdf_path, mime_type="application/pdf")

        page_prompt = (
            "Review this entire PDF brochure. Find ALL pages that contain contact "
            "information, specifically mobile numbers or phone numbers. "
            "Return a flat JSON list of integer page numbers (1-indexed). "
            "Example: [1, 15, 16]. If none are found, return []."
        )
        page_resp = client.models.generate_content(
            model=model_name,
            contents=[uploaded_pdf, page_prompt],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.0,
            ),
        )
        client.files.delete(name=uploaded_pdf.name)

        try:
            cleaned_text = _clean_json_str(page_resp.text)
            parsed_pages = json.loads(cleaned_text)
            if isinstance(parsed_pages, list):
                target_pages = [int(p) for p in parsed_pages if str(p).isdigit() or isinstance(p, (int, float))]
            elif isinstance(parsed_pages, dict):
                pages_val = parsed_pages.get("pages") or parsed_pages.get("page_numbers") or []
                target_pages = [int(p) for p in pages_val if str(p).isdigit() or isinstance(p, (int, float))]
            else:
                target_pages = [int(p) for p in re.findall(r"\d+", cleaned_text)]
            target_pages = sorted(set(target_pages))
        except Exception:
            target_pages = [int(p) for p in re.findall(r"\d+", page_resp.text)]
            target_pages = sorted(set(target_pages))

        _log(f"Contact pages identified: {target_pages}")

        # If no contact pages — just copy with correct name
        if not target_pages:
            os.makedirs(output_dir, exist_ok=True)
            out_path = os.path.join(output_dir, final_filename)
            shutil.copy2(pdf_path, out_path)
            response.update(status=True, data=os.path.abspath(out_path),
                            reason="No contact pages found. Original copied.")
            return response

        # ── STEP 2: Apply masks page by page ────────────────────────────────
        doc = fitz.open(pdf_path)
        pages_masked = 0

        for page_num in target_pages:
            page_idx = page_num - 1
            if page_idx < 0 or page_idx >= len(doc):
                _log(f"Page {page_num} out of range, skipping.")
                continue

            _log(f"Processing page {page_num}…")
            page = doc[page_idx]

            pix = page.get_pixmap(dpi=200, colorspace=fitz.csRGB, alpha=False)
            tmp_img = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
            tmp_img.close()
            pix.save(tmp_img.name)

            # Upload page image for bounding-box detection
            uploaded_img = _upload_and_wait(client, tmp_img.name, mime_type="image/png")

            bbox_sys = (
                "You are an object detection model. Find all phone numbers in the image. "
                "CRITICAL: Your bounding box MUST encompass BOTH the phone number AND its "
                "preceding text label such as 'Call:', 'Sales Office:', 'Mob:', 'Ph:', etc. "
                "Return a JSON list of objects each containing 'box_2d'. "
                "Coordinates must be [ymin, xmin, ymax, xmax] normalized to 0-1000."
            )
            bbox_resp = client.models.generate_content(
                model=model_name,
                contents=[uploaded_img, "Locate all phone numbers with prefix labels and return bounding boxes."],
                config=types.GenerateContentConfig(
                    system_instruction=bbox_sys,
                    response_mime_type="application/json",
                    temperature=0.0,
                ),
            )
            client.files.delete(name=uploaded_img.name)

            try:
                raw_boxes = json.loads(_clean_json_str(bbox_resp.text))
                if isinstance(raw_boxes, dict):
                    if "box_2d" in raw_boxes:
                        boxes = [raw_boxes]
                    elif "boxes" in raw_boxes and isinstance(raw_boxes["boxes"], list):
                        boxes = raw_boxes["boxes"]
                    else:
                        boxes = []
                elif isinstance(raw_boxes, list):
                    boxes = raw_boxes
                else:
                    boxes = []
            except json.JSONDecodeError:
                _log(f"Failed to parse bounding boxes for page {page_num}, skipping.")
                os.remove(tmp_img.name)
                continue

            if not boxes:
                _log(f"No bounding boxes on page {page_num}.")
                os.remove(tmp_img.name)
                continue

            # ── Apply paint-over ────────────────────────────────────────────
            pil_img = Image.open(tmp_img.name).convert("RGBA")
            w, h = pil_img.size
            margin = 25

            for item in boxes:
                if "box_2d" not in item:
                    continue
                y1n, x1n, y2n, x2n = item["box_2d"]
                ax1 = max(0, int(x1n / 1000 * w) - margin)
                ay1 = max(0, int(y1n / 1000 * h) - margin)
                ax2 = min(w, int(x2n / 1000 * w) + margin)
                ay2 = min(h, int(y2n / 1000 * h) + margin)

                ax1, ax2 = sorted([ax1, ax2])
                ay1, ay2 = sorted([ay1, ay2])
                if ax1 >= ax2 or ay1 >= ay2:
                    continue

                region = pil_img.crop((ax1, ay1, ax2, ay2))
                blurred = Image.fromarray(cv2.GaussianBlur(np.array(region), (51, 51), 0))
                bg_color = get_dominant_color(pil_img, ax1, ay1, ax2, ay2, w, h)
                overlay = Image.new("RGBA", blurred.size, bg_color)
                patch = Image.alpha_composite(blurred, overlay)

                tmp_patch = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
                tmp_patch.close()
                patch.save(tmp_patch.name)

                pw, ph = page.rect.width, page.rect.height
                rect = fitz.Rect(
                    ax1 / w * pw, ay1 / h * ph,
                    ax2 / w * pw, ay2 / h * ph,
                )
                page.insert_image(rect, filename=tmp_patch.name)
                os.remove(tmp_patch.name)

            pages_masked += 1
            os.remove(tmp_img.name)

        # ── STEP 3: Save with exact output filename ──────────────────────────
        os.makedirs(output_dir, exist_ok=True)
        out_path = os.path.join(output_dir, final_filename)

        if pages_masked > 0:
            doc.save(out_path, deflate=True)
            _log(f"Masked PDF saved: {out_path}")
        else:
            doc.close()
            shutil.copy2(pdf_path, out_path)
            _log(f"No masks applied. Original copied to: {out_path}")
            response.update(status=True, data=os.path.abspath(out_path),
                            reason="Contact pages found but no boxes detected. Original copied.")
            return response

        doc.close()
        response.update(status=True, data=os.path.abspath(out_path),
                        reason=f"Masked {pages_masked} page(s) successfully.")
        return response

    except Exception as e:
        logger.exception(f"Critical masking error: {e}")
        response["reason"] = str(e)
        return response
