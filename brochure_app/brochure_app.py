"""
Brochure Analyzer — Reflex App Entry Point
"""

import reflex as rx
from brochure_app.pages.index import index
from brochure_app.state import AppState


app = rx.App(
    stylesheets=[
        "https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=Outfit:wght@400;600;700;800&family=Fira+Code:wght@400;500&display=swap",
    ],
    style={
        "box_sizing": "border-box",
        "margin": "0",
        "padding": "0",
    },
)

app.add_page(index, route="/", title="Brochure Analyzer | AI Logo & Masking Tool")
