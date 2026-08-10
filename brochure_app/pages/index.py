"""
Brochure Analyzer
"""

import reflex as rx
from brochure_app.state import AppState


# ──────────────────────────────────────────────────────────────────────────────
# Minimalist Style Tokens (White Background & Black Text Theme)
# ──────────────────────────────────────────────────────────────────────────────

CARD_STYLE = dict(
    background="#ffffff",
    border="1px solid #e4e4e7",
    border_radius="12px",
    box_shadow="0 2px 12px rgba(0,0,0,0.04)",
    width="100%",
)


def card(padding: str = "1.75rem", border_override: str = None, background_override: str = None, **extra) -> dict:
    """Build a minimal light card style dictionary."""
    styles = {**CARD_STYLE, "padding": padding}
    if border_override:
        styles["border"] = border_override
    if background_override:
        styles["background"] = background_override
    styles.update(extra)
    return styles


def _mono_tag(text: str) -> rx.Component:
    """Minimalist light badge."""
    return rx.box(
        rx.text(text, font_size="0.7rem", font_weight="600", letter_spacing="0.05em", color="#27272a"),
        padding="0.2rem 0.65rem",
        background="#f4f4f5",
        border="1px solid #e4e4e7",
        border_radius="6px",
    )


def log_console(logs) -> rx.Component:
    """Minimalist light log console."""
    return rx.box(
        rx.vstack(
            rx.hstack(
                rx.box(
                    width="6px",
                    height="6px",
                    border_radius="50%",
                    background="#09090b",
                ),
                rx.text(
                    "Activity Log",
                    color="#52525b",
                    font_size="0.75rem",
                    font_weight="600",
                    letter_spacing="0.05em",
                ),
                align="center",
                spacing="2",
            ),
            rx.box(
                rx.foreach(
                    logs,
                    lambda msg: rx.text(
                        "-> " + msg,
                        font_size="0.75rem",
                        color="#09090b",
                        font_family="'Fira Code', monospace",
                        line_height="1.6",
                    ),
                ),
                width="100%",
                max_height="200px",
                overflow_y="auto",
                padding="0.5rem 0",
            ),
            spacing="2",
            width="100%",
        ),
        background="#f4f4f5",
        border="1px solid #e4e4e7",
        border_radius="10px",
        padding="1rem",
        width="100%",
    )


def _download_btn(on_click, label: str, icon_name: str) -> rx.Component:
    """Clean high-contrast black action button on white theme."""
    return rx.button(
        rx.hstack(
            rx.icon(icon_name, size=15, color="#ffffff"),
            rx.text(label, font_size="0.85rem", font_weight="600", color="#ffffff"),
            spacing="2",
            align="center",
        ),
        on_click=on_click,
        background="#09090b",
        color="#ffffff",
        border_radius="8px",
        padding="0.6rem 1.25rem",
        cursor="pointer",
        border="1px solid #09090b",
        _hover={"background": "#27272a", "border_color": "#27272a"},
        transition="all 0.15s ease",
    )


def _error_box(msg) -> rx.Component:
    return rx.box(
        rx.hstack(
            rx.icon("circle_alert", size=15, color="#dc2626"),
            rx.text(msg, color="#dc2626", font_size="0.85rem"),
            spacing="2",
            align="center",
        ),
        background="#fef2f2",
        border="1px solid #fecaca",
        border_radius="8px",
        padding="0.75rem 1rem",
        width="100%",
    )


# ──────────────────────────────────────────────────────────────────────────────
# API Key Card
# ──────────────────────────────────────────────────────────────────────────────

def api_key_card() -> rx.Component:
    return rx.box(
        rx.vstack(
            rx.hstack(
                rx.icon("key", size=16, color="#52525b"),
                rx.text(
                    "Gemini API Key",
                    color="#09090b",
                    font_weight="600",
                    font_size="0.9rem",
                ),
                align="center",
                spacing="2",
            ),
            rx.hstack(
                rx.input(
                    placeholder="",
                    value=AppState.api_key,
                    on_change=AppState.set_api_key,
                    type=rx.cond(AppState.api_key_visible, "text", "password"),
                    width="100%",
                    background="#ffffff",
                    border="1px solid #d4d4d8",
                    border_radius="8px",
                    color="#09090b",
                    padding="0.6rem 0.9rem",
                    font_size="0.85rem",
                    _placeholder={"color": "#040404"},
                    _focus={
                        "border_color": "#09090b",
                        "outline": "none",
                    },
                ),
                rx.button(
                    rx.cond(
                        AppState.api_key_visible,
                        rx.icon("eye_off", size=15, color="#52525b"),
                        rx.icon("eye", size=15, color="#52525b"),
                    ),
                    on_click=AppState.toggle_api_key_visible,
                    background="#ffffff",
                    border="1px solid #d4d4d8",
                    border_radius="8px",
                    color="#52525b",
                    padding="0.6rem 0.8rem",
                    cursor="pointer",
                    _hover={"background": "#f4f4f5", "color": "#09090b"},
                ),
                spacing="2",
                width="100%",
                align="center",
            ),
            rx.text(
                "Key is stored securely in your local browser session only.",
                font_size="0.75rem",
                color="#71717a",
            ),
            spacing="2",
            width="100%",
        ),
        **card(padding="1.25rem 1.5rem"),
    )


# ──────────────────────────────────────────────────────────────────────────────
# Tab Navigation Bar
# ──────────────────────────────────────────────────────────────────────────────

def tab_bar() -> rx.Component:
    tabs = [
        ("single", "file_text", "Single PDF"),
        ("batch", "layers", "Batch Processing (Excel)"),
    ]
    return rx.hstack(
        *[
            rx.button(
                rx.hstack(
                    rx.icon(
                        icon,
                        size=14,
                        color=rx.cond(AppState.active_tab == tab, "#ffffff", "#52525b"),
                    ),
                    rx.text(label, font_size="0.85rem", font_weight="600"),
                    spacing="2",
                    align="center",
                ),
                on_click=AppState.set_active_tab(tab),
                background=rx.cond(
                    AppState.active_tab == tab,
                    "#09090b",
                    "transparent",
                ),
                color=rx.cond(
                    AppState.active_tab == tab,
                    "#ffffff",
                    "#52525b",
                ),
                border=rx.cond(
                    AppState.active_tab == tab,
                    "1px solid #09090b",
                    "1px solid transparent",
                ),
                border_radius="8px",
                padding="0.55rem 1.25rem",
                cursor="pointer",
                transition="all 0.15s ease",
                _hover={
                    "color": rx.cond(AppState.active_tab == tab, "#ffffff", "#09090b"),
                    "background": rx.cond(AppState.active_tab == tab, "#09090b", "#e4e4e7"),
                },
            )
            for tab, icon, label in tabs
        ],
        spacing="2",
        background="#f4f4f5",
        border="1px solid #e4e4e7",
        border_radius="10px",
        padding="0.3rem",
        width="100%",
    )


# ──────────────────────────────────────────────────────────────────────────────
# Single PDF Tab Component
# ──────────────────────────────────────────────────────────────────────────────

def single_tab() -> rx.Component:
    mode_items = [
        ("mask", "Mask Contact Info"),
        ("logo", "Extract Logo Only"),
        ("both", "Mask + Extract Logo"),
    ]

    return rx.vstack(
        # Upload zone
        rx.cond(
            AppState.single_filename != "",
            rx.box(
                rx.hstack(
                    rx.icon("file_text", size=24, color="#09090b"),
                    rx.vstack(
                        rx.text(AppState.single_filename, color="#09090b", font_weight="600", font_size="0.9rem"),
                        rx.text("PDF loaded & ready", color="#71717a", font_size="0.75rem"),
                        spacing="0",
                        align="start",
                    ),
                    rx.spacer(),
                    rx.button(
                        "Remove",
                        on_click=AppState.clear_single,
                        background="#ffffff",
                        border="1px solid #d4d4d8",
                        border_radius="6px",
                        color="#52525b",
                        font_size="0.75rem",
                        padding="0.35rem 0.75rem",
                        cursor="pointer",
                        _hover={"background": "#f4f4f5", "color": "#09090b"},
                    ),
                    spacing="3",
                    align="center",
                    width="100%",
                ),
                border="1px solid #d4d4d8",
                border_radius="10px",
                padding="1.25rem 1.5rem",
                width="100%",
                background="#fafafa",
            ),
            rx.upload(
                rx.vstack(
                    rx.icon("cloud_upload", size=32, color="#52525b"),
                    rx.text("Drop your PDF brochure here", color="#09090b", font_weight="600", font_size="0.9rem"),
                    rx.text("or click to select file from device", color="#71717a", font_size="0.8rem"),
                    spacing="2",
                    align="center",
                ),
                id="single_pdf_upload",
                accept={".pdf": ["application/pdf"]},
                multiple=False,
                on_drop=AppState.handle_single_upload(
                    rx.upload_files(upload_id="single_pdf_upload")
                ),
                border="1px dashed #d4d4d8",
                border_radius="10px",
                padding="2.5rem 1.5rem",
                width="100%",
                background="#fafafa",
                cursor="pointer",
                _hover={"border_color": "#09090b", "background": "#f4f4f5"},
                transition="all 0.15s ease",
            ),
        ),

        # Mode selector
        rx.box(
            rx.vstack(
                rx.text(
                    "Select Processing Mode",
                    color="#52525b",
                    font_size="0.8rem",
                    font_weight="600",
                ),
                rx.hstack(
                    *[
                        rx.button(
                            label,
                            on_click=AppState.set_single_mode(val),
                            background=rx.cond(
                                AppState.single_mode == val,
                                "#09090b",
                                "#ffffff",
                            ),
                            color=rx.cond(
                                AppState.single_mode == val,
                                "#ffffff",
                                "#52525b",
                            ),
                            border=rx.cond(
                                AppState.single_mode == val,
                                "1px solid #09090b",
                                "1px solid #e4e4e7",
                            ),
                            border_radius="6px",
                            padding="0.5rem 1rem",
                            font_size="0.8rem",
                            font_weight="600",
                            cursor="pointer",
                            transition="all 0.15s ease",
                            _hover={
                                "color": rx.cond(AppState.single_mode == val, "#ffffff", "#09090b"),
                                "background": rx.cond(AppState.single_mode == val, "#09090b", "#f4f4f5"),
                            },
                        )
                        for val, label in mode_items
                    ],
                    spacing="2",
                    flex_wrap="wrap",
                ),
                spacing="2",
                align="start",
            ),
            **card(padding="1.25rem 1.5rem"),
        ),

        # Error message
        rx.cond(
            AppState.single_error != "",
            _error_box(AppState.single_error),
            rx.box(),
        ),

        # Action Button
        rx.button(
            rx.cond(
                AppState.single_processing,
                rx.hstack(
                    rx.spinner(size="2", color="#ffffff"),
                    rx.text("Processing PDF…", color="#ffffff"),
                    spacing="2",
                ),
                rx.hstack(
                    rx.icon("play", size=15, color="#ffffff"),
                    rx.text("Run Analysis", color="#ffffff", font_weight="600"),
                    spacing="2",
                ),
            ),
            on_click=AppState.process_single,
            is_disabled=AppState.single_processing,
            background="#09090b",
            color="#ffffff",
            border_radius="8px",
            padding="0.8rem",
            font_weight="600",
            font_size="0.95rem",
            cursor="pointer",
            border="1px solid #09090b",
            width="100%",
            _hover={"background": "#27272a"},
            transition="all 0.15s ease",
        ),

        # Console Output
        rx.cond(
            AppState.single_logs.length() > 0,
            log_console(AppState.single_logs),
            rx.box(),
        ),

        # Results Display Card
        rx.cond(
            AppState.single_done,
            rx.box(
                rx.vstack(
                    rx.hstack(
                        rx.icon("circle_check", size=18, color="#09090b"),
                        rx.text(
                            "Processing Complete",
                            color="#09090b",
                            font_weight="700",
                            font_size="0.95rem",
                        ),
                        spacing="2",
                        align="center",
                    ),
                    rx.cond(
                        AppState.single_has_logo & (AppState.single_logo_b64 != ""),
                        rx.vstack(
                            rx.text("Extracted Project Logo", font_size="0.78rem", font_weight="600", color="#52525b"),
                            rx.box(
                                rx.image(
                                    src="data:image/jpeg;base64," + AppState.single_logo_b64,
                                    max_height="140px",
                                    object_fit="contain",
                                    border_radius="6px",
                                ),
                                background="#ffffff",
                                border="1px solid #e4e4e7",
                                border_radius="8px",
                                padding="0.75rem",
                                align_self="start",
                            ),
                            spacing="2",
                            align="start",
                        ),
                        rx.box(),
                    ),
                    rx.hstack(
                        rx.cond(
                            AppState.single_has_masked,
                            _download_btn(
                                AppState.download_masked_pdf,
                                "Download Masked PDF",
                                "download",
                            ),
                            rx.box(),
                        ),
                        rx.cond(
                            AppState.single_has_logo,
                            _download_btn(
                                AppState.download_logo,
                                "Download Logo (JPEG)",
                                "image",
                            ),
                            rx.box(),
                        ),
                        spacing="3",
                        flex_wrap="wrap",
                    ),
                    spacing="3",
                    width="100%",
                ),
                **card(
                    padding="1.5rem",
                    border_override="1px solid #e4e4e7",
                    background_override="#fafafa",
                ),
            ),
            rx.box(),
        ),

        spacing="4",
        width="100%",
    )


# ──────────────────────────────────────────────────────────────────────────────
# Batch Results Table Component
# ──────────────────────────────────────────────────────────────────────────────

def batch_results_table() -> rx.Component:
    return rx.box(
        rx.vstack(
            rx.text(
                "Execution Summary",
                font_size="0.8rem",
                font_weight="700",
                color="#09090b",
            ),
            rx.box(
                rx.table.root(
                    rx.table.header(
                        rx.table.row(
                            rx.table.column_header_cell("XID"),
                            rx.table.column_header_cell("Status"),
                            rx.table.column_header_cell("Masked File"),
                            rx.table.column_header_cell("Logo Output"),
                            rx.table.column_header_cell("Size (MB)"),
                        )
                    ),
                    rx.table.body(
                        rx.foreach(
                            AppState.batch_results,
                            lambda item: rx.table.row(
                                rx.table.cell(rx.text(item["XID"], color="#09090b")),
                                rx.table.cell(
                                    rx.cond(
                                        item["Status"] == "Success",
                                        _mono_tag("SUCCESS"),
                                        _mono_tag("FAILED"),
                                    )
                                ),
                                rx.table.cell(rx.text(item["Masked PDF"], color="#09090b")),
                                rx.table.cell(rx.text(item["Logo"], color="#09090b")),
                                rx.table.cell(rx.text(item["Size (MB)"], color="#09090b")),
                            ),
                        )
                    ),
                    width="100%",
                ),
                max_height="240px",
                overflow_y="auto",
                width="100%",
                border="1px solid #e4e4e7",
                border_radius="8px",
                background="#ffffff",
            ),
            spacing="2",
            width="100%",
        ),
        width="100%",
        margin_top="0.5rem",
    )


# ──────────────────────────────────────────────────────────────────────────────
# Batch Excel Tab Component
# ──────────────────────────────────────────────────────────────────────────────

def batch_tab() -> rx.Component:
    mode_items = [
        ("mask", "Mask Contact Info"),
        ("logo", "Extract Logo Only"),
        ("both", "Mask + Extract Logo"),
    ]

    return rx.vstack(
        # Informational note
        rx.box(
            rx.hstack(
                rx.icon("info", size=15, color="#52525b"),
                rx.text(
                    "Upload Excel spreadsheet containing XID (output ID) and Brochure Link (PDF URL) columns.",
                    color="#52525b",
                    font_size="0.82rem",
                ),
                spacing="2",
                align="center",
                flex_wrap="wrap",
            ),
            background="#f4f4f5",
            border="1px solid #e4e4e7",
            border_radius="8px",
            padding="0.75rem 1rem",
            width="100%",
        ),

        # File Dropzone or Selection Status
        rx.cond(
            AppState.batch_filename != "",
            rx.box(
                rx.hstack(
                    rx.icon("table", size=24, color="#09090b"),
                    rx.vstack(
                        rx.text(
                            AppState.batch_filename,
                            color="#09090b",
                            font_weight="600",
                            font_size="0.9rem",
                        ),
                        rx.text("Excel file loaded & ready", color="#71717a", font_size="0.75rem"),
                        spacing="0",
                        align="start",
                    ),
                    rx.spacer(),
                    rx.button(
                        "Remove",
                        on_click=AppState.clear_batch,
                        background="#ffffff",
                        border="1px solid #d4d4d8",
                        border_radius="6px",
                        color="#52525b",
                        font_size="0.75rem",
                        padding="0.35rem 0.75rem",
                        cursor="pointer",
                        _hover={"background": "#f4f4f5", "color": "#09090b"},
                    ),
                    spacing="3",
                    align="center",
                    width="100%",
                ),
                **card(
                    padding="1.25rem 1.5rem",
                    border_override="1px solid #d4d4d8",
                    background_override="#fafafa",
                ),
            ),
            rx.upload(
                rx.vstack(
                    rx.icon("table", size=32, color="#52525b"),
                    rx.text("Drop your Excel file here", color="#09090b", font_weight="600", font_size="0.9rem"),
                    rx.text("Supports .xlsx and .xls formats", color="#71717a", font_size="0.8rem"),
                    spacing="2",
                    align="center",
                ),
                id="batch_excel_upload",
                accept={
                    ".xlsx": ["application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"],
                    ".xls": ["application/vnd.ms-excel"],
                },
                multiple=False,
                on_drop=AppState.handle_batch_upload(
                    rx.upload_files(upload_id="batch_excel_upload")
                ),
                border="1px dashed #d4d4d8",
                border_radius="10px",
                padding="2.5rem 1.5rem",
                width="100%",
                background="#fafafa",
                cursor="pointer",
                _hover={"border_color": "#09090b", "background": "#f4f4f5"},
                transition="all 0.15s ease",
            ),
        ),

        # Mode & Concurrency Settings Card
        rx.box(
            rx.vstack(
                rx.vstack(
                    rx.text(
                        "Select Processing Mode",
                        color="#52525b",
                        font_size="0.8rem",
                        font_weight="600",
                    ),
                    rx.hstack(
                        *[
                            rx.button(
                                label,
                                on_click=AppState.set_batch_mode(val),
                                background=rx.cond(
                                    AppState.batch_mode == val,
                                    "#09090b",
                                    "#ffffff",
                                ),
                                color=rx.cond(
                                    AppState.batch_mode == val,
                                    "#ffffff",
                                    "#52525b",
                                ),
                                border=rx.cond(
                                    AppState.batch_mode == val,
                                    "1px solid #09090b",
                                    "1px solid #e4e4e7",
                                ),
                                border_radius="6px",
                                padding="0.5rem 1rem",
                                font_size="0.8rem",
                                font_weight="600",
                                cursor="pointer",
                                transition="all 0.15s ease",
                                _hover={
                                    "color": rx.cond(AppState.batch_mode == val, "#ffffff", "#09090b"),
                                    "background": rx.cond(AppState.batch_mode == val, "#09090b", "#f4f4f5"),
                                },
                            )
                            for val, label in mode_items
                        ],
                        spacing="2",
                        flex_wrap="wrap",
                    ),
                    spacing="2",
                    align="start",
                    width="100%",
                ),
                rx.box(height="1px", background="#e4e4e7", width="100%"),
                rx.hstack(
                    rx.icon("cpu", size=14, color="#52525b"),
                    rx.text(
                        "Processing Mode: Sequential (Optimized for 512 MB RAM limit)",
                        color="#52525b",
                        font_size="0.8rem",
                        font_weight="500",
                    ),
                    align="center",
                    spacing="2",
                ),
                spacing="3",
                width="100%",
            ),
            **card(padding="1.25rem 1.5rem"),
        ),

        # Error display
        rx.cond(
            AppState.batch_error != "",
            _error_box(AppState.batch_error),
            rx.box(),
        ),

        # Process Button
        rx.button(
            rx.cond(
                AppState.batch_processing,
                rx.hstack(
                    rx.spinner(size="2", color="#ffffff"),
                    rx.text("Processing Batch Tasks…", color="#ffffff"),
                    spacing="2",
                ),
                rx.hstack(
                    rx.icon("play", size=15, color="#ffffff"),
                    rx.text("Start Batch Processing", color="#ffffff", font_weight="600"),
                    spacing="2",
                ),
            ),
            on_click=AppState.process_batch,
            is_disabled=AppState.batch_processing,
            background="#09090b",
            color="#ffffff",
            border_radius="8px",
            padding="0.8rem",
            font_weight="600",
            font_size="0.95rem",
            cursor="pointer",
            border="1px solid #09090b",
            width="100%",
            _hover={"background": "#27272a"},
            transition="all 0.15s ease",
        ),

        # Logs Console
        rx.cond(
            AppState.batch_logs.length() > 0,
            log_console(AppState.batch_logs),
            rx.box(),
        ),

        # Results Summary
        rx.cond(
            AppState.batch_done,
            rx.box(
                rx.vstack(
                    rx.hstack(
                        rx.icon("circle_check", size=18, color="#09090b"),
                        rx.text(
                            "Batch Execution Complete",
                            color="#09090b",
                            font_weight="700",
                            font_size="0.95rem",
                        ),
                        spacing="2",
                        align="center",
                    ),
                    rx.text(
                        AppState.batch_progress_rows.to_string() + " items processed.",
                        color="#52525b",
                        font_size="0.82rem",
                    ),
                    rx.hstack(
                        rx.cond(
                            AppState.batch_has_zip,
                            _download_btn(
                                AppState.download_batch_zip,
                                "Download ZIP Archive",
                                "package",
                            ),
                            rx.box(),
                        ),
                        rx.cond(
                            AppState.batch_has_summary,
                            _download_btn(
                                AppState.download_batch_summary,
                                "Download Summary (Excel)",
                                "file_spreadsheet",
                            ),
                            rx.box(),
                        ),
                        spacing="3",
                        flex_wrap="wrap",
                    ),
                    rx.cond(
                        AppState.batch_results.length() > 0,
                        batch_results_table(),
                        rx.box(),
                    ),
                    spacing="3",
                    width="100%",
                ),
                **card(
                    padding="1.5rem",
                    border_override="1px solid #e4e4e7",
                    background_override="#fafafa",
                ),
            ),
            rx.box(),
        ),

        spacing="4",
        width="100%",
    )


# ──────────────────────────────────────────────────────────────────────────────
# Header Component
# ──────────────────────────────────────────────────────────────────────────────

def hero() -> rx.Component:
    return rx.vstack(
        rx.hstack(
            rx.box(
                rx.icon("scan_line", size=24, color="#ffffff"),
                background="#09090b",
                border_radius="10px",
                padding="0.6rem",
            ),
            rx.vstack(
                rx.heading(
                    "Brochure Analyzer",
                    size="7",
                    color="#09090b",
                    font_weight="700",
                    letter_spacing="-0.03em",
                ),
                rx.text(
                    "Automated logo extraction & contact info masking platform",
                    color="#52525b",
                    font_size="0.85rem",
                ),
                spacing="0",
                align="start",
            ),
            rx.spacer(),
            rx.button(
                rx.icon("log_out", size=14),
                "Logout",
                on_click=AppState.logout,
                size="2",
                variant="outline",
                style={
                    "border": "1px solid #e4e4e7",
                    "color": "#52525b",
                    "cursor": "pointer",
                    "_hover": {"background": "#f4f4f5"},
                },
            ),
            spacing="3",
            align="center",
            width="100%",
        ),
        spacing="3",
        padding_bottom="0.25rem",
    )


# ──────────────────────────────────────────────────────────────────────────────
# Login Page
# ──────────────────────────────────────────────────────────────────────────────

def login_page() -> rx.Component:
    return rx.center(
        rx.vstack(
            rx.text(
                "Brochure Analyzer",
                font_size="1.5rem",
                font_weight="800",
                color="#09090b",
                font_family="'Outfit', sans-serif",
            ),
            rx.text(
                "Sign in to continue",
                font_size="0.85rem",
                color="#71717a",
                margin_top="-0.25rem",
            ),
            rx.vstack(
                rx.text("Username", font_size="0.8rem", font_weight="500", color="#3f3f46"),
                rx.input(
                    placeholder="Enter username",
                    value=AppState.login_username,
                    on_change=AppState.set_login_username,
                    width="100%",
                    size="3",
                    style={"border": "1px solid #e4e4e7", "background": "#ffffff"},
                ),
                spacing="1",
                width="100%",
            ),
            rx.vstack(
                rx.text("Password", font_size="0.8rem", font_weight="500", color="#3f3f46"),
                rx.input(
                    placeholder="Enter password",
                    value=AppState.login_password,
                    on_change=AppState.set_login_password,
                    type="password",
                    width="100%",
                    size="3",
                    style={"border": "1px solid #e4e4e7", "background": "#ffffff"},
                ),
                spacing="1",
                width="100%",
            ),
            rx.cond(
                AppState.login_error != "",
                rx.text(AppState.login_error, color="#dc2626", font_size="0.8rem"),
                rx.box(),
            ),
            rx.button(
                "Sign In",
                on_click=AppState.login,
                width="100%",
                size="3",
                style={
                    "background": "#09090b",
                    "color": "#ffffff",
                    "font_weight": "600",
                    "cursor": "pointer",
                    "_hover": {"background": "#27272a"},
                },
            ),
            spacing="3",
            width="100%",
            max_width="360px",
            background="#ffffff",
            border="1px solid #e4e4e7",
            border_radius="12px",
            box_shadow="0 2px 12px rgba(0,0,0,0.04)",
            padding="2rem",
        ),
        width="100%",
        min_height="100vh",
        background="#f9fafb",
    )


# ──────────────────────────────────────────────────────────────────────────────
# Main Page View
# ──────────────────────────────────────────────────────────────────────────────

def index() -> rx.Component:
    return rx.box(
        rx.cond(
            AppState.logged_in == False,
            login_page(),
            rx.center(
                rx.vstack(
                    hero(),
                    api_key_card(),

                    # Tab Navigation
                    rx.center(tab_bar(), width="100%"),

                    # Active Tab Panel
                    rx.box(
                        rx.cond(
                            AppState.active_tab == "single",
                            single_tab(),
                            batch_tab(),
                        ),
                        **card(padding="1.75rem"),
                    ),

                    # Minimalist Footer
                    rx.text(
                        "",
                        color="#a1a1aa",
                        font_size="0.75rem",
                        text_align="center",
                    ),

                    # Hidden WebSocket Keep-Alive Ping (every 15s to prevent Fly.dev container idle timeout)
                    rx.box(
                        rx.button(
                            id="keep_alive_btn",
                            on_click=AppState.keep_alive,
                            style={"display": "none"},
                        ),
                        rx.script(
                            "setInterval(() => { const b = document.getElementById('keep_alive_btn'); if (b) b.click(); }, 15000);"
                        ),
                        style={"display": "none"},
                    ),

                    spacing="5",
                    width="100%",
                    max_width="720px",
                    padding="2.5rem 1rem",
                ),
                width="100%",
                min_height="100vh",
            ),
        ),
        font_family="'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
        background="#ffffff",
        min_height="100vh",
    )
