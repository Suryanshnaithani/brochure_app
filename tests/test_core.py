import io
import os
import tempfile
import unittest
import pandas as pd
import fitz

from brochure_app.core.compression import compress_pdf_to_limit
from brochure_app.core.masking import _clean_json_str
from brochure_app.core.logo_extraction import _clean_json_str as clean_logo_json
from brochure_app.core.batch_processor import process_excel_batch, _clean_xid


class TestBrochureCore(unittest.TestCase):

    def test_json_cleaner(self):
        json_raw = "```json\n[1, 2, 3]\n```"
        cleaned = _clean_json_str(json_raw)
        self.assertEqual(cleaned, "[1, 2, 3]")
        self.assertEqual(clean_logo_json("   [{\"box_2d\": [0,0,100,100]}]   "), "[{\"box_2d\": [0,0,100,100]}]")

    def test_clean_xid(self):
        self.assertEqual(_clean_xid(376659), "376659")
        self.assertEqual(_clean_xid("376659.0"), "376659")
        self.assertEqual(_clean_xid(" 512043 "), "512043")
        self.assertEqual(_clean_xid(None), "")

    def test_pdf_compression_small_file(self):
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
        tmp.close()
        doc = fitz.open()
        page = doc.new_page(width=595, height=842)
        page.insert_text((50, 50), "Test PDF for Brochure App")
        doc.save(tmp.name)
        doc.close()

        try:
            res = compress_pdf_to_limit(tmp.name, tmp.name, target_bytes=24 * 1024 * 1024)
            self.assertTrue(res["status"])
            self.assertGreater(res["size_bytes"], 0)
        finally:
            if os.path.exists(tmp.name):
                os.remove(tmp.name)

    def test_excel_batch_column_mapping(self):
        # Create Excel in-memory with alternative column headers (lowercase 'id' and 'url')
        df = pd.DataFrame([{"id": "101", "url": "https://example.com/test.pdf"}])
        buf = io.BytesIO()
        df.to_excel(buf, index=False)
        excel_bytes = buf.getvalue()

        # Call batch process without real API key to check structure handling
        res = process_excel_batch(excel_bytes, api_key="test_dummy_key", max_workers=1)
        # Status might complete or fail row downloads, but missing columns error should not fire
        self.assertNotIn("Excel missing columns", res.get("reason", ""))


if __name__ == "__main__":
    unittest.main()
