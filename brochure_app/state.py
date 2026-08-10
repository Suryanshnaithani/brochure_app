"""
Brochure Analyzer — Reflex Application
State management for both single-PDF and batch-Excel modes.

Files are stored temporarily on the server and served via Reflex's
rx.download() mechanism to avoid sending large base64 blobs over WebSocket.
"""

import base64
import io
import os
import tempfile
import zipfile
from typing import Optional

import reflex as rx

from brochure_app.core.batch_processor import process_single_pdf_full, process_excel_batch


# ──────────────────────────────────────────────────────────────────────────────
# State
# ──────────────────────────────────────────────────────────────────────────────

class AppState(rx.State):
    # ── Auth / Settings ────────────────────────────────────────────────────────
    api_key: str = ""
    api_key_visible: bool = False

    # ── Tab selection ──────────────────────────────────────────────────────────
    active_tab: str = "single"  # "single" | "batch"

    # ── Single PDF mode ────────────────────────────────────────────────────────
    single_filename: str = ""
    single_pdf_bytes_b64: str = ""   # base64 of uploaded PDF bytes
    single_mode: str = "both"        # "mask" | "logo" | "both"

    single_processing: bool = False
    single_logs: list[str] = []
    single_done: bool = False
    single_error: str = ""

    # Download availability flags
    single_has_masked: bool = False
    single_has_logo: bool = False
    single_logo_b64: str = ""
    single_size_mb: float = 0.0

    # Temp file paths (server-side, used for downloads)
    _single_masked_path: str = ""
    _single_logo_path: str = ""

    # ── Batch mode ─────────────────────────────────────────────────────────────
    batch_filename: str = ""
    batch_excel_bytes_b64: str = ""
    batch_mode: str = "both"  # "mask" | "logo" | "both"
    batch_max_workers: int = 1  # Concurrency worker count (max 1 for 512MB RAM)

    batch_processing: bool = False
    batch_logs: list[str] = []
    batch_done: bool = False
    batch_error: str = ""
    batch_progress_rows: int = 0
    batch_results: list[dict] = []

    batch_has_zip: bool = False
    batch_has_summary: bool = False
    _batch_zip_path: str = ""
    _batch_summary_path: str = ""

    # ── Helpers ────────────────────────────────────────────────────────────────

    def set_api_key(self, value: str):
        self.api_key = value

    def toggle_api_key_visible(self):
        self.api_key_visible = not self.api_key_visible

    def set_active_tab(self, tab: str):
        self.active_tab = tab

    def set_single_mode(self, mode: str):
        self.single_mode = mode

    def set_batch_mode(self, mode: str):
        self.batch_mode = mode

    def set_batch_max_workers(self, count: int):
        self.batch_max_workers = min(count, 1)

    def keep_alive(self):
        """Keep-alive ping to maintain WebSocket connection on Reflex Cloud."""
        pass

    # ── Single PDF upload ──────────────────────────────────────────────────────

    async def handle_single_upload(self, files: list[rx.UploadFile]):
        if not files:
            return
        file = files[0]
        data = await file.read()
        self.single_filename = file.filename
        self.single_pdf_bytes_b64 = base64.b64encode(data).decode()
        self.single_done = False
        self.single_error = ""
        self.single_logs = []
        self.single_has_masked = False
        self.single_has_logo = False
        self.single_logo_b64 = ""
        self._single_masked_path = ""
        self._single_logo_path = ""

    def clear_single(self):
        self.single_filename = ""
        self.single_pdf_bytes_b64 = ""
        self.single_done = False
        self.single_error = ""
        self.single_logs = []
        self.single_has_masked = False
        self.single_has_logo = False
        self.single_logo_b64 = ""
        self.single_size_mb = 0.0
        self._single_masked_path = ""
        self._single_logo_path = ""

    # ── Single PDF process ─────────────────────────────────────────────────────

    def process_single(self):
        if not self.api_key.strip():
            self.single_error = "Please enter your Gemini API key first."
            return
        if not self.single_pdf_bytes_b64:
            self.single_error = "Please upload a PDF first."
            return

        self.single_processing = True
        self.single_done = False
        self.single_error = ""
        self.single_logs = ["Starting processing…"]
        self.single_has_masked = False
        self.single_has_logo = False
        self.single_logo_b64 = ""
        yield

        try:
            pdf_bytes = base64.b64decode(self.single_pdf_bytes_b64)
            logs_local: list[str] = []

            def callback(msg: str):
                logs_local.append(msg)

            result = process_single_pdf_full(
                pdf_bytes=pdf_bytes,
                filename=self.single_filename,
                api_key=self.api_key.strip(),
                mode=self.single_mode,
                progress_callback=callback,
            )

            self.single_logs = logs_local

            if result["status"]:
                # Save outputs to temp files for download
                if result.get("masked_pdf_bytes"):
                    tmp = tempfile.NamedTemporaryFile(
                        delete=False, suffix=".pdf",
                        prefix="masked_"
                    )
                    tmp.write(result["masked_pdf_bytes"])
                    tmp.close()
                    self._single_masked_path = tmp.name
                    self.single_has_masked = True
                    self.single_size_mb = result.get("size_mb", 0.0)

                if result.get("logo_bytes"):
                    tmp = tempfile.NamedTemporaryFile(
                        delete=False, suffix=".jpeg",
                        prefix="logo_"
                    )
                    tmp.write(result["logo_bytes"])
                    tmp.close()
                    self._single_logo_path = tmp.name
                    self.single_has_logo = True
                    self.single_logo_b64 = base64.b64encode(result["logo_bytes"]).decode()

                self.single_done = True
            else:
                self.single_error = result.get("reason", "Unknown error")

        except Exception as e:
            self.single_error = str(e)

        self.single_processing = False

    # ── Single PDF downloads ───────────────────────────────────────────────────

    def download_masked_pdf(self):
        """Serve the masked PDF as a download."""
        if not self._single_masked_path or not os.path.exists(self._single_masked_path):
            self.single_error = "Masked PDF not available."
            return
        with open(self._single_masked_path, "rb") as f:
            data = f.read()
        return rx.download(data=data, filename=self.single_filename)

    def download_logo(self):
        """Serve the logo as a download."""
        if not self._single_logo_path or not os.path.exists(self._single_logo_path):
            self.single_error = "Logo not available."
            return
        with open(self._single_logo_path, "rb") as f:
            data = f.read()
        stem = os.path.splitext(self.single_filename)[0]
        return rx.download(data=data, filename=f"{stem}_logo.jpeg")

    # ── Batch Excel upload ─────────────────────────────────────────────────────

    async def handle_batch_upload(self, files: list[rx.UploadFile]):
        if not files:
            return
        file = files[0]
        data = await file.read()
        self.batch_filename = file.filename
        self.batch_excel_bytes_b64 = base64.b64encode(data).decode()
        self.batch_done = False
        self.batch_error = ""
        self.batch_logs = []
        self.batch_results = []
        self.batch_has_zip = False
        self.batch_has_summary = False
        self._batch_zip_path = ""
        self._batch_summary_path = ""

    def clear_batch(self):
        self.batch_filename = ""
        self.batch_excel_bytes_b64 = ""
        self.batch_done = False
        self.batch_error = ""
        self.batch_logs = []
        self.batch_results = []
        self.batch_has_zip = False
        self.batch_has_summary = False
        self.batch_progress_rows = 0
        self._batch_zip_path = ""
        self._batch_summary_path = ""

    # ── Batch process ──────────────────────────────────────────────────────────

    def process_batch(self):
        if not self.api_key.strip():
            self.batch_error = "Please enter your Gemini API key first."
            return
        if not self.batch_excel_bytes_b64:
            self.batch_error = "Please upload an Excel file first."
            return

        self.batch_processing = True
        self.batch_done = False
        self.batch_error = ""
        self.batch_logs = ["Starting batch processing…"]
        self.batch_results = []
        self.batch_has_zip = False
        self.batch_has_summary = False
        self.batch_progress_rows = 0
        yield

        try:
            excel_bytes = base64.b64decode(self.batch_excel_bytes_b64)
            logs_local: list[str] = []

            def callback(msg: str):
                logs_local.append(msg)

            result = process_excel_batch(
                excel_bytes=excel_bytes,
                api_key=self.api_key.strip(),
                mode=self.batch_mode,
                progress_callback=callback,
                max_workers=self.batch_max_workers,
            )

            self.batch_logs = logs_local
            self.batch_results = result.get("results", [])
            self.batch_progress_rows = len(self.batch_results)

            if result["status"]:
                if result.get("zip_bytes"):
                    tmp = tempfile.NamedTemporaryFile(
                        delete=False, suffix=".zip", prefix="brochures_"
                    )
                    tmp.write(result["zip_bytes"])
                    tmp.close()
                    self._batch_zip_path = tmp.name
                    self.batch_has_zip = True

                if result.get("summary_excel_bytes"):
                    tmp = tempfile.NamedTemporaryFile(
                        delete=False, suffix=".xlsx", prefix="summary_"
                    )
                    tmp.write(result["summary_excel_bytes"])
                    tmp.close()
                    self._batch_summary_path = tmp.name
                    self.batch_has_summary = True

                self.batch_done = True
            else:
                self.batch_error = result.get("reason", "Unknown error")

        except Exception as e:
            self.batch_error = str(e)

        self.batch_processing = False

    # ── Batch downloads ────────────────────────────────────────────────────────

    def download_batch_zip(self):
        if not self._batch_zip_path or not os.path.exists(self._batch_zip_path):
            self.batch_error = "ZIP not available."
            return
        with open(self._batch_zip_path, "rb") as f:
            data = f.read()
        return rx.download(data=data, filename="brochures_output.zip")

    def download_batch_summary(self):
        if not self._batch_summary_path or not os.path.exists(self._batch_summary_path):
            self.batch_error = "Summary not available."
            return
        with open(self._batch_summary_path, "rb") as f:
            data = f.read()
        return rx.download(data=data, filename="processing_summary.xlsx")
