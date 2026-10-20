"""
app.py - Library Management System
Production ASGI Entry Point for Unified Campus Workspace

Architecture:
- Native FastAPI + Modern Web Application (Pixel-perfect matching of reference screenshots).
- Served via Uvicorn on port 8501.
- Automatically recognized by Streamlit 1.66+ ASGI discovery (`streamlit run app.py`)
  as well as direct Python invocation (`python app.py`).
"""

from __future__ import annotations

import sys
from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import JSONResponse
import server

# Create the top-level FastAPI ASGI app for Streamlit and Uvicorn
app = FastAPI(
    title="Library Management System",
    description="REST API & Web Interface powering the modern Library Management System.",
    version="2.1.0",
)

# Healthcheck endpoints for container supervisors and Streamlit Community Cloud
@app.get("/_stcore/health")
@app.get("/healthz")
def healthcheck() -> JSONResponse:
    """Return healthy status for cloud load balancers and container supervisors."""
    return JSONResponse(content={"status": "ok", "app": "Library Management System"})

# Mount the complete server application (static frontend + REST API endpoints)
app.mount("/", server.app)

if __name__ == "__main__":
    import uvicorn
    print("\n" + "=" * 60)
    print(" [*] Launching Library Management System on http://localhost:8501")
    print("=" * 60 + "\n")
    uvicorn.run("app:app", host="0.0.0.0", port=8501, reload=False)
