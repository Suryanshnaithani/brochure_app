"""
Excel batch processor.
Reads an Excel with columns 'XID' and 'Brochure Link'.
Downloads each PDF, masks it, extracts logo, compresses, zips.
All outputs written to temp files on disk — nothing held in RAM.
"""

import gc
import os
import io
import logging
import shutil
import tempfile
import zipfile
from typing import Callable, Optional

import requests
import pandas as pd

from .masking import mask_brochure
from .logo_extraction import extract_project_logo
from .compression import compress_pdf_to_limit

logger = logging.getLogger(__name__)

REQUIRED_COLS = {"XID", "Brochure Link"}


def _download_pdf(url: str, dest_dir: str) -> Optional[str]:
    """Download a PDF from *url* to *dest_dir* and return local path, or None."""
    try:
        r = requests.get(url, timeout=60, stream=True)
        r.raise_for_status()
        fname = os.path.basename(url.split("?")[0])
        if not fname.lower().endswith(".pdf"):
            fname = "brochure.pdf"
        local = os.path.join(dest_dir, fname)
        with open(local, "wb") as f:
            for chunk in r.iter_content(chunk_size=65536):
                f.write(chunk)
        return local
    except Exception as e:
        logger.error(f"Download failed for {url}: {e}")
        return None


def _process_one_row(
    xid: str,
    url: str,
    api_key: str,
    work_dir: str,
    masked_dir: str,
    logos_dir: str,
    mode: str = "both",
    progress_callback: Optional[Callable] = None,
) -> dict:
    """Process a single XID+URL row end-to-end. All outputs stay on disk."""

    def _log(msg: str):
        logger.info(f"[{xid}] {msg}")
        if progress_callback:
            progress_callback(f"[{xid}] {msg}")

    result = {
        "XID": xid,
        "Status": "Failed",
        "Masked PDF": "N/A" if mode == "logo" else "",
        "Logo": "N/A" if mode == "mask" else "",
        "Size (MB)": "N/A" if mode == "logo" else "",
        "Notes": "",
    }

    if not url or str(url).lower() == "nan":
        result["Notes"] = "Empty URL"
        return result

    # ── Download ─────────────────────────────────────────────────────────────
    _log("Downloading PDF…")
    row_dl_dir = os.path.join(work_dir, "downloads", xid)
    os.makedirs(row_dl_dir, exist_ok=True)
    pdf_path = _download_pdf(str(url).strip(), row_dl_dir)

    if not pdf_path:
        result["Notes"] = "Download failed"
        return result

    masked_path = None
    size_mb = 0.0
    notes_list = []

    # ── Masking ───────────────────────────────────────────────────────────────
    if mode in ("mask", "both"):
        _log("Masking…")
        mask_result = mask_brochure(
            pdf_path=pdf_path,
            api_key=api_key,
            output_dir=masked_dir,
            output_filename=f"{xid}.pdf",
            progress_callback=_log,
        )

        if not mask_result["status"]:
            result["Notes"] = f"Masking failed: {mask_result['reason']}"
            return result

        masked_path = mask_result["data"]
        notes_list.append(mask_result["reason"])

        # ── Compression to ≤24 MB ─────────────────────────────────────────────────
        _log("Compressing…")
        comp_result = compress_pdf_to_limit(
            pdf_path=masked_path,
            output_path=masked_path,
            progress_callback=_log,
        )
        size_mb = comp_result.get("size_bytes", 0) / 1e6

    # ── Logo Extraction ───────────────────────────────────────────────────────
    logo_filename = "N/A"
    if mode in ("logo", "both"):
        _log("Extracting logo…")
        logo_result = extract_project_logo(
            pdf_path=pdf_path,
            api_key=api_key,
            output_dir=logos_dir,
            output_filename=xid,
            progress_callback=_log,
        )
        if logo_result["status"]:
            logo_filename = os.path.basename(logo_result["data"])
        else:
            logo_filename = "Not found"
        notes_list.append(logo_result.get("reason", ""))

    result.update(
        Status="Success",
        **{"Masked PDF": os.path.basename(masked_path) if masked_path else "N/A"},
        Logo=logo_filename if mode in ("logo", "both") else "N/A",
        **{"Size (MB)": f"{size_mb:.2f}" if mode in ("mask", "both") else "N/A"},
        Notes="; ".join([n for n in notes_list if n]),
    )
    return result


def _clean_xid(val) -> str:
    """Clean string/numeric XID to avoid '.0' float suffixes."""
    if pd.isna(val):
        return ""
    s = str(val).strip()
    if s.endswith(".0"):
        s = s[:-2]
    return s


def process_excel_batch(
    excel_bytes: bytes,
    api_key: str,
    mode: str = "both",
    progress_callback: Optional[Callable] = None,
) -> dict:
    """
    Process all rows from an Excel file sequentially.
    Returns file paths on disk — no large byte arrays in memory.

    Returns:
        dict with keys:
            status (bool), zip_path (str), summary_path (str),
            reason (str), results (list[dict])
    """
    response = {
        "status": False,
        "zip_path": None,
        "summary_path": None,
        "reason": "",
        "results": [],
    }

    def _log(msg: str):
        logger.info(msg)
        if progress_callback:
            progress_callback(msg)

    # Free the excel_bytes immediately after reading
    try:
        df = pd.read_excel(io.BytesIO(excel_bytes))
    except Exception as e:
        response["reason"] = f"Could not read Excel: {e}"
        return response
    del excel_bytes

    # Normalise column names
    col_map = {}
    for c in df.columns:
        c_clean = str(c).strip()
        c_lower = c_clean.lower()
        if c_lower in ("xid", "id", "x_id"):
            col_map[c] = "XID"
        elif c_lower in ("brochure link", "brochure_link", "brochurelink", "url", "link", "brochure"):
            col_map[c] = "Brochure Link"
        else:
            col_map[c] = c_clean
    df = df.rename(columns=col_map)

    missing = REQUIRED_COLS - set(df.columns)
    if missing:
        response["reason"] = f"Excel missing columns: {missing}. Expected: XID, Brochure Link (or url/link)"
        return response

    work_dir = tempfile.mkdtemp(prefix="brochure_batch_")
    masked_dir = os.path.join(work_dir, "masked")
    logos_dir = os.path.join(work_dir, "logos")
    os.makedirs(masked_dir, exist_ok=True)
    os.makedirs(logos_dir, exist_ok=True)

    rows = []
    for _, r in df.iterrows():
        xid = _clean_xid(r.get("XID"))
        url = str(r.get("Brochure Link", "")).strip()
        if xid and url and url.lower() != "nan":
            rows.append((xid, url))
    del df

    _log(f"Starting batch of {len(rows)} rows in mode '{mode}'…")
    results = []

    for idx, (xid, url) in enumerate(rows, 1):
        _log(f"[{idx}/{len(rows)}] Processing XID {xid}…")
        try:
            row_result = _process_one_row(
                xid, url, api_key, work_dir, masked_dir, logos_dir, mode, progress_callback,
            )
        except Exception as e:
            row_result = {"XID": xid, "Status": "Failed", "Notes": str(e)}
        results.append(row_result)
        _log(f"[{xid}] Done → {row_result.get('Status')}")

        # Clean up downloaded PDF for this row
        row_dl_dir = os.path.join(work_dir, "downloads", xid)
        if os.path.exists(row_dl_dir):
            shutil.rmtree(row_dl_dir, ignore_errors=True)

        gc.collect()

    response["results"] = results

    # ── Build ZIP to temp file ────────────────────────────────────────────────
    _log("Building output ZIP…")
    zip_path = os.path.join(work_dir, "output.zip")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for fname in os.listdir(masked_dir):
            fpath = os.path.join(masked_dir, fname)
            zf.write(fpath, arcname=f"masked_pdfs/{fname}")
        for fname in os.listdir(logos_dir):
            fpath = os.path.join(logos_dir, fname)
            zf.write(fpath, arcname=f"logos/{fname}")
    response["zip_path"] = zip_path

    # ── Build summary Excel to temp file ──────────────────────────────────────
    summary_path = os.path.join(work_dir, "summary.xlsx")
    pd.DataFrame(results).to_excel(summary_path, index=False)
    response["summary_path"] = summary_path

    response.update(status=True, reason=f"Processed {len(results)} rows.")
    _log("Batch complete.")
    return response


def process_single_pdf_full(
    pdf_bytes: bytes,
    filename: str,
    api_key: str,
    mode: str = "both",
    progress_callback: Optional[Callable] = None,
) -> dict:
    """
    Process a single uploaded PDF. Returns file paths on disk — no bytes in memory.

    Returns:
        dict with status, masked_pdf_path, logo_path, reason, size_mb
    """
    response = {
        "status": False,
        "masked_pdf_path": None,
        "logo_path": None,
        "reason": "",
        "size_mb": 0.0,
    }

    def _log(msg: str):
        logger.info(msg)
        if progress_callback:
            progress_callback(msg)

    work_dir = tempfile.mkdtemp(prefix="brochure_single_")
    input_path = os.path.join(work_dir, filename)
    output_dir = os.path.join(work_dir, "out")
    logo_dir = os.path.join(work_dir, "logos")
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(logo_dir, exist_ok=True)

    with open(input_path, "wb") as f:
        f.write(pdf_bytes)
    del pdf_bytes  # Free immediately

    stem = os.path.splitext(filename)[0]

    try:
        if mode in ("mask", "both"):
            _log("Masking PDF…")
            mask_result = mask_brochure(
                pdf_path=input_path,
                api_key=api_key,
                output_dir=output_dir,
                output_filename=filename,
                progress_callback=_log,
            )
            if not mask_result["status"]:
                response["reason"] = f"Masking failed: {mask_result['reason']}"
                return response

            masked_path = mask_result["data"]

            _log("Compressing…")
            compress_pdf_to_limit(
                pdf_path=masked_path,
                output_path=masked_path,
                progress_callback=_log,
            )

            response["masked_pdf_path"] = masked_path
            response["size_mb"] = os.path.getsize(masked_path) / 1e6

        if mode in ("logo", "both"):
            _log("Extracting logo…")
            logo_result = extract_project_logo(
                pdf_path=input_path,
                api_key=api_key,
                output_dir=logo_dir,
                output_filename=stem,
                progress_callback=_log,
            )
            if logo_result["status"]:
                response["logo_path"] = logo_result["data"]

        response.update(status=True, reason="Processing complete.")
        return response

    except Exception as e:
        logger.exception(e)
        response["reason"] = str(e)
        return response
