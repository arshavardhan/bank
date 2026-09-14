"""FastAPI application entrypoint for AI Financial Statement Analysis Agent."""

import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from app.config.settings import settings
from app.database.session import init_db
from app.api.routes import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: initialize database tables
    init_db()
    yield
    # Shutdown logic if needed


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "Production-ready AI Financial Statement Analysis Agent. "
        "Allows uploading bank statements in CSV, Excel, PDF, or image formats, "
        "normalizes transactions into a unified schema, deterministically computes financial metrics, "
        "and uses LangGraph with result validation to deliver accurate, non-hallucinated financial insights."
    ),
    lifespan=lifespan
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files for sample statements
if os.path.exists("sample_data"):
    app.mount("/sample_data", StaticFiles(directory="sample_data"), name="sample_data")

# Mount API routes
app.include_router(router)


@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    svg_icon = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><circle cx="50" cy="50" r="48" fill="#4f46e5"/><text x="50" y="68" font-size="52" font-family="Arial" font-weight="bold" fill="white" text-anchor="middle">$</text></svg>'''
    return Response(content=svg_icon, media_type="image/svg+xml")


@app.get("/", response_class=HTMLResponse, summary="Interactive Web Dashboard")
def root():
    template_path = os.path.join(os.path.dirname(__file__), "templates", "index.html")
    if os.path.exists(template_path):
        with open(template_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse(content="<h1>Financial Statement AI Analyst</h1><p>Visit <a href='/docs'>/docs</a> for API documentation.</p>")


@app.get("/api/info", summary="API Service Metadata")
def api_info():
    return {
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "documentation": "/docs",
        "health": "/health",
        "endpoints": {
            "upload_statement": "POST /upload",
            "ask_agent": "POST /ask",
            "list_transactions": "GET /transactions",
            "statement_summary": "GET /summary"
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
