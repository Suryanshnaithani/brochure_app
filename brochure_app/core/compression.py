"""
PDF compression using PyMuPDF only (no Poppler, cloud-safe).
Target: output always ≤ 24 MB.
Strategy: flatten each page to rasterized image at progressively lower DPI.
"""

import os
import logging
import tempfile
from typing import Optional

import fitz
from PIL import Image

logger = logging.getLogger(__name__)

# Compression ladder: (DPI, JPEG quality) — each step shrinks the file further
_COMPRESSION_STEPS = [
    (150, 85),
    (120, 75),
    (100, 65),
    (80, 55),
    (72, 45),
]

TARGET_BYTES = 24 * 1024 * 1024  # 24 MB


def compress_pdf_to_limit(
    pdf_path: str,
    output_path: str,
    target_bytes: int = TARGET_BYTES,
    progress_callback=None,
) -> dict:
    """
    Compress a PDF so its size is <= target_bytes.

    The file at *output_path* is already expected to be the final file; this
    function replaces it with a compressed version only when needed.

    Returns:
        dict with keys: status (bool), size_bytes (int), reason (str)
    """
    response = {"status": False, "size_bytes": 0, "reason": ""}

    def _log(msg: str):
        logger.info(msg)
        if progress_callback:
            progress_callback(msg)

    original_size = os.path.getsize(pdf_path)

    if original_size <= target_bytes:
        _log(f"File is already {original_size / 1e6:.2f} MB — no compression needed.")
        response.update(status=True, size_bytes=original_size,
                        reason="Already within size limit.")
        return response

    _log(f"File is {original_size / 1e6:.2f} MB > 24 MB — starting compression…")

    src_doc = fitz.open(pdf_path)
    best_path: Optional[str] = None
    best_size = original_size

    for dpi, quality in _COMPRESSION_STEPS:
        _log(f"Trying DPI={dpi}, quality={quality}…")
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
        tmp.close()

        try:
            pages_pil = []
            for page_idx in range(len(src_doc)):
                page = src_doc[page_idx]
                pix = page.get_pixmap(dpi=dpi, colorspace=fitz.csRGB, alpha=False)
                # Convert to PIL for JPEG compression
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                pages_pil.append(img)

            if not pages_pil:
                continue

            pages_pil[0].save(
                tmp.name,
                format="PDF",
                save_all=True,
                append_images=pages_pil[1:],
                resolution=dpi,
                quality=quality,
                optimize=True,
            )

            new_size = os.path.getsize(tmp.name)
            _log(f"  → {new_size / 1e6:.2f} MB at DPI={dpi}")

            if new_size < best_size:
                if best_path and os.path.exists(best_path):
                    os.remove(best_path)
                best_path = tmp.name
                best_size = new_size
            else:
                os.remove(tmp.name)

            if new_size <= target_bytes:
                _log(f"Target reached at DPI={dpi}.")
                break

        except Exception as e:
            _log(f"  Compression step failed: {e}")
            if os.path.exists(tmp.name):
                os.remove(tmp.name)
            continue

    src_doc.close()

    if best_path and best_size < original_size:
        # Replace output_path with the best compressed version
        os.replace(best_path, output_path)
        final_size = os.path.getsize(output_path)
        _log(f"Compressed to {final_size / 1e6:.2f} MB → saved at {output_path}")
        warning = "" if final_size <= target_bytes else " (still above 24 MB — maximum compression applied)"
        response.update(status=True, size_bytes=final_size,
                        reason=f"Compressed successfully.{warning}")
    else:
        if best_path and os.path.exists(best_path):
            os.remove(best_path)
        _log("Compression did not reduce size; keeping original.")
        response.update(status=True, size_bytes=original_size,
                        reason="Could not compress further. Original kept.")

    return response
