# Brochure Analyzer — Deployment Guide

## Project Structure

```
brochure_app/
├── rxconfig.py                      # Reflex configuration
├── requirements.txt                 # Python dependencies
├── .reflex.toml                     # Cloud deploy config
├── assets/                          # Static assets
└── brochure_app/
    ├── __init__.py
    ├── brochure_app.py              # App entry point
    ├── state.py                     # App state management
    ├── pages/
    │   ├── __init__.py
    │   └── index.py                 # Main UI page
    └── core/
        ├── __init__.py
        ├── masking.py               # Phone number masking (Gemini + PyMuPDF)
        ├── logo_extraction.py       # Project logo extraction (Gemini)
        ├── compression.py           # PDF compression to ≤24 MB (PyMuPDF only)
        └── batch_processor.py      # Excel batch processing orchestrator
```

## Local Development

```bash
cd brochure_app
pip install -r requirements.txt
reflex run
```

Open http://localhost:3000

## Deploy to Render (Docker Web Service)

1. Push your repository to GitHub or GitLab.
2. Go to **[Render Dashboard](https://dashboard.render.com)**.
3. Click **New +** → **Web Service**.
4. Connect your GitHub repository.
5. Render will automatically detect `Dockerfile` and `render.yaml`. Select **Docker** as environment.
6. Click **Create Web Service**.

---

## Excel Format (Batch Mode)

| XID | Brochure Link |
|-----|---------------|
| 376659 | https://example.com/brochure.pdf |
| 512043 | https://example.com/doc.pdf |

- **XID** → output filename (`{XID}.pdf`)
- **Brochure Link** → direct PDF download URL

## API Key

Get a free key at https://aistudio.google.com/app/apikey  
Paste it in the app — never stored server-side.

## Features

| Feature | Details |
|---------|---------|
| Phone masking | Gemini vision detects phones, blurred color-matched patch applied |
| Logo extraction | First 2 pages scanned, project logo cropped as JPEG |
| PDF compression | PyMuPDF-only progressive DPI reduction, targets ≤24 MB |
| Exact filename | Single: same as upload; Batch: XID.pdf |
| Excel batch | XID + Brochure Link, 3 concurrent workers (free-tier safe) |
| Live logs | Real-time processing updates in browser |
| Downloads | Masked PDF, logo JPEG, batch ZIP, summary Excel |

## Customization

### Change the model
In `core/masking.py` and `core/logo_extraction.py`:
```python
model_name = "gemini-3-flash-preview"
```

### Adjust compression
In `core/compression.py`:
```python
_COMPRESSION_STEPS = [
    (150, 85),   # DPI=150, JPEG quality=85  (lightest)
    (120, 75),
    (100, 65),
    (80, 55),
    (72, 45),    # Most aggressive
]
```
