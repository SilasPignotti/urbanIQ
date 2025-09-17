"""
Frontend route handlers for serving HTML templates.

Provides web interface endpoints for the urbanIQ Berlin geodata assistant,
including the main chat interface and static file serving integration.
"""

from pathlib import Path

import structlog
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

logger = structlog.get_logger("urbaniq.api.frontend")

router = APIRouter(tags=["frontend"])

# Configure Jinja2 templates
TEMPLATE_DIR = Path(__file__).parent.parent / "frontend" / "templates"
templates = Jinja2Templates(directory=str(TEMPLATE_DIR))


@router.get("/", response_class=HTMLResponse, include_in_schema=False)
async def index(request: Request) -> HTMLResponse:
    """
    Serve the main chat interface page.

    Returns:
        HTMLResponse: The main index page with chat interface
    """
    logger.info("Serving main chat interface")

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "title": "urbanIQ Berlin - Geodaten-Assistent",
            "description": "Intelligente Geodaten-Aggregation für Berlin",
        },
    )


@router.get("/health-ui", response_class=HTMLResponse, include_in_schema=False)
async def health_ui(_request: Request) -> HTMLResponse:
    """
    Serve a simple health check page for monitoring.

    Returns:
        HTMLResponse: Simple health status page
    """
    logger.info("Serving health UI page")

    # Simple health page without full template complexity
    from datetime import datetime

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    html_content = f"""
    <!DOCTYPE html>
    <html lang="de">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>urbanIQ Berlin - System Status</title>
        <style>
            body {{ font-family: system-ui, sans-serif; margin: 40px; }}
            .status {{ padding: 20px; border-radius: 8px; background: #f0fdf4; border: 1px solid #22c55e; }}
            .timestamp {{ color: #666; font-size: 0.9em; margin-top: 10px; }}
        </style>
    </head>
    <body>
        <h1>urbanIQ Berlin - System Status</h1>
        <div class="status">
            <h2>✅ System Online</h2>
            <p>Frontend-Interface ist verfügbar und funktionsfähig.</p>
            <div class="timestamp">Letzte Prüfung: {timestamp}</div>
        </div>
        <p><a href="/">← Zurück zum Geodaten-Assistenten</a></p>
    </body>
    </html>
    """

    return HTMLResponse(content=html_content, status_code=200)
