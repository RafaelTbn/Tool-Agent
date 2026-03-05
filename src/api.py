"""FastAPI entrypoint for the tool-enabled agent."""

from __future__ import annotations

from fastapi import FastAPI
from pydantic import BaseModel

from src.main import build_agent

app = FastAPI(title="Tool-Agent API")
agent = build_agent()


class QueryRequest(BaseModel):
    query: str


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/query")
def query(request: QueryRequest) -> dict:
    return agent.handle_query(query=request.query)
