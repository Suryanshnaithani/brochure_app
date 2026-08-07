import reflex as rx


config = rx.Config(
    app_name="brochure_app",
    # Free-tier friendly settings
    db_url="sqlite:///reflex.db",
    # Set to 100 MB to allow PDF uploads
    upload_max_file_size=100 * 1024 * 1024,  # 100 MB
    cors_allowed_origins=["*"],
    plugins=[
        rx.plugins.RadixThemesPlugin(),
        rx.plugins.SitemapPlugin(),
    ],
)
