from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.routes import router

app = FastAPI(
    title="Learning Assistant",
    description="智能学伴多智能体项目的最小可运行后端",
    version="0.1.0",
)

app.include_router(router)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

frontend_dir = Path(__file__).resolve().parent / "frontend"
app.mount("/assets", StaticFiles(directory=frontend_dir), name="assets")


@app.get("/")
def frontend() -> FileResponse:
    return FileResponse(
        frontend_dir / "index.html",
        headers={"Cache-Control": "no-store, no-cache, must-revalidate"},
    )


@app.get("/health")
def healthcheck() -> dict[str, str]:
    return {"status": "ok", "message": "Learning Assistant API is running."}


@app.get("/{file_name}")
def frontend_asset(file_name: str) -> FileResponse:
    path = frontend_dir / file_name
    if path.is_file() and path.suffix in {".html", ".css", ".js"}:
        return FileResponse(
            path,
            headers={"Cache-Control": "no-store, no-cache, must-revalidate"},
        )
    raise HTTPException(status_code=404, detail="Frontend file not found.")
