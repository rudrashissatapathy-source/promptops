"""Main FastAPI application for PromptOps."""

from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from promptops.server.routes import router

UI_DIR = Path(__file__).resolve().parent.parent / "ui"

app = FastAPI(
    title="PromptOps Platform",
    description="Controlled LLM Generation Platform with Multi-Backend Routing, AST Self-Repair, and Regression Runner.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)

# Mount UI static assets
if UI_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(UI_DIR)), name="static")

    @app.get("/", include_in_schema=False)
    async def serve_index():
        return FileResponse(UI_DIR / "index.html")


@app.get("/health", tags=["system"])
async def health_check():
    """System health check endpoint."""
    return {"status": "healthy", "service": "promptops", "version": "0.1.0"}
