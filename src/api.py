"""FastAPI entrypoint for the tool-enabled agent."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from pydantic import BaseModel

from src.main import build_runtime

app = FastAPI(title="Tool-Agent API")
agent, logger = build_runtime()


class QueryRequest(BaseModel):
    query: str
    include_debug: bool = False


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/query")
def query(request: QueryRequest) -> dict:
    return agent.handle_query(query=request.query, include_debug=request.include_debug)


@app.get("/logs")
def get_logs() -> dict:
    log_path = Path(logger.get_log_file_path())
    return {
        "status": "ok",
        "entries": logger.get_history(),
        "count": len(logger.entries),
        "log_file": str(log_path),
        "log_file_exists": log_path.exists(),
    }
