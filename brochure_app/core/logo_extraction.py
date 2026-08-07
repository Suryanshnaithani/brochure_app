"""
Project-logo extraction — scans first 2 pages, crops logo, saves as JPEG.
"""

import os
import json
import tempfile
import logging
import time
from typing import Optional

import fitz
from PIL import Image
from google import genai
from google.genai import types

import re

Image.MAX_IMAGE_PIXELS = None
logger = logging.getLogger(__name__)


def _clean_json_str(text: str) -> str:
    """Clean markdown backticks from JSON responses."""
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```$", "", text)
    return text.strip()


def _upload_and_wait(client: genai.Client, file_path: str, mime_type: str = None):
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


def extract_project_logo(
    pdf_path: str,
    api_key: str,
    output_dir: str = "Extracted_Logos",
    output_filename: Optional[str] = None,
    progress_callback=None,
) -> dict:
    """
    Scan the first 2 pages of *pdf_path* and extract the project logo.

    Args:
        pdf_path:         Path to the PDF.
        api_key:          Gemini API key.
        output_dir:       Directory to save the logo PNG.
        output_filename:  Base name for the logo file (without extension).
                          Defaults to the PDF stem.
        progress_callback: Optional callable(msg: str).

    Returns:
        dict with keys: status (bool), data (path | None), reason (str)
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

        stem = output_filename or os.path.splitext(os.path.basename(pdf_path))[0]
        doc = fitz.open(pdf_path)
        pages_to_scan = min(2, len(doc))
        logo_found = False

        for page_idx in range(pages_to_scan):
            _log(f"Scanning page {page_idx + 1} for project logo…")
            page = doc[page_idx]

            pix = page.get_pixmap(dpi=300, colorspace=fitz.csRGB, alpha=False)
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
            tmp.close()
            pix.save(tmp.name)

            uploaded = _upload_and_wait(client, tmp.name, mime_type="image/png")

            sys_inst = (
                "You are an expert object detection model specializing in real estate brochures. "
                "Locate the primary 'Project Logo' — the stylized name, graphic, or typography "
                "of the specific building or development being advertised. "
                "Do NOT select the builder/developer/corporate logo or generic text. "
                "Return a JSON list with a single object containing 'box_2d'. "
                "Coordinates must be [ymin, xmin, ymax, xmax] normalized to 0-1000. "
                "If no project logo is found, return []."
            )
            resp = client.models.generate_content(
                model=model_name,
                contents=[uploaded, "Locate the main Project Logo. Return its bounding box only."],
                config=types.GenerateContentConfig(
                    system_instruction=sys_inst,
                    response_mime_type="application/json",
                    temperature=0.0,
                ),
            )
            client.files.delete(name=uploaded.name)

            try:
                raw_boxes = json.loads(_clean_json_str(resp.text))
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
                _log(f"Could not parse logo boxes for page {page_idx + 1}.")
                os.remove(tmp.name)
                continue

            if not boxes:
                _log(f"No project logo on page {page_idx + 1}.")
                os.remove(tmp.name)
                continue

            item = boxes[0]
            if "box_2d" not in item:
                os.remove(tmp.name)
                continue

            pil_img = Image.open(tmp.name).convert("RGBA")
            iw, ih = pil_img.size
            y1n, x1n, y2n, x2n = item["box_2d"]
            pad = 15
            ax1 = max(0, int(x1n / 1000 * iw) - pad)
            ay1 = max(0, int(y1n / 1000 * ih) - pad)
            ax2 = min(iw, int(x2n / 1000 * iw) + pad)
            ay2 = min(ih, int(y2n / 1000 * ih) + pad)

            logo_crop = pil_img.crop((ax1, ay1, ax2, ay2))

            os.makedirs(output_dir, exist_ok=True)
            out_path = os.path.join(output_dir, f"{stem}_logo.jpeg")
            logo_crop = logo_crop.convert("RGB")
            logo_crop.save(out_path, format="JPEG")

            _log(f"Logo saved: {out_path}")
            response.update(status=True, data=os.path.abspath(out_path),
                            reason=f"Logo extracted from page {page_idx + 1}.")
            logo_found = True
            os.remove(tmp.name)
            break

        doc.close()

        if not logo_found:
            response["reason"] = "No project logo found in first 2 pages."

        return response

    except Exception as e:
        logger.exception(f"Critical logo extraction error: {e}")
        response["reason"] = str(e)
        return response
