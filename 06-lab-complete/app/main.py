"""
Production AI Agent — Part 6 Final Project.
"""
from contextlib import asynccontextmanager
from datetime import datetime, timezone
import json
import logging
import sys
import time
from typing import Optional

from fastapi import Depends, FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.auth import verify_api_key
from app.config import settings
from app.cost_guard import check_budget, record_cost
from app.rate_limiter import check_rate_limit
from app.redis_client import r, redis_healthy
from utils.mock_llm import ask as llm_ask


class JsonFormatter(logging.Formatter):
    """Định dạng mỗi dòng log thành một JSON object hợp lệ."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "lvl": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        for attr in ("event", "path", "status", "ms"):
            val = getattr(record, attr, None)
            if val is not None:
                payload[attr] = val
        return json.dumps(payload, ensure_ascii=False)


def _configure_logging() -> logging.Logger:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger("app")
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(getattr(logging, settings.log_level.upper(), logging.INFO))
    root.propagate = False
    return logging.getLogger("app.main")


logger = _configure_logging()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    logger.info("Agent starting", extra={"event": "startup"})
    try:
        yield
    finally:
        logger.info("Agent shutting down gracefully", extra={"event": "shutdown"})
        if r is not None:
            try:
                r.close()
            except Exception:
                pass


app = FastAPI(title="Production AI Agent", lifespan=lifespan)


class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)
    user_id: Optional[str] = None


@app.exception_handler(Exception)
async def unhandled_exception_handler(_request: Request, exc: Exception):
    logger.error("Unhandled error: %s", type(exc).__name__, extra={"event": "error", "status": 500})
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


@app.get("/health")
def health():
    """Liveness check: luôn trả 200 khi process còn chạy."""
    logger.info("Health check", extra={"event": "health", "path": "/health", "status": 200})
    return {"status": "ok"}


@app.get("/ready")
def ready():
    """Readiness check: 200 khi Redis kết nối được, 503 khi mất kết nối."""
    if redis_healthy():
        logger.info("Readiness ok", extra={"event": "ready", "path": "/ready", "status": 200})
        return {"status": "ready", "redis": "ok"}
    logger.warning("Readiness failed", extra={"event": "ready", "path": "/ready", "status": 503})
    return JSONResponse(status_code=503, content={"status": "not ready", "redis": "down"})


@app.post("/ask")
def ask(body: AskRequest, api_key: str = Depends(verify_api_key)):
    start = time.perf_counter()
    check_rate_limit(api_key)
    check_budget()

    answer = llm_ask(body.question)
    input_tokens = max(1, len(body.question.split()))
    output_tokens = max(1, len(answer.split()))
    cost = record_cost(input_tokens, output_tokens)

    elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
    logger.info(
        "Handled /ask",
        extra={"event": "request", "path": "/ask", "status": 200, "ms": elapsed_ms},
    )
    return {"question": body.question, "answer": answer, "cost_usd": round(cost, 6)}
