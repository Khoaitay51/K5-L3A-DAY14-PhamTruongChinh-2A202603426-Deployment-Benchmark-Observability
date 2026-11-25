"""
Cost guard (tiêu chí 8) — theo dõi chi phí LLM trong Redis.
"""
from datetime import datetime, timezone
import logging

from fastapi import HTTPException
import redis

from app.config import settings
from app.redis_client import r

logger = logging.getLogger(__name__)

# Giá USD / 1K tokens (tham khảo gpt-4o-mini)
PRICE_INPUT_PER_1K = 0.00015
PRICE_OUTPUT_PER_1K = 0.0006


def _daily_budget_key() -> str:
    return f"cost:daily:{datetime.now(timezone.utc).strftime('%Y-%m-%d')}"


def check_budget() -> None:
    """Gọi TRƯỚC khi gọi LLM. Hết budget → raise HTTPException(status_code=402)."""
    if r is None:
        return
    try:
        spent = float(r.get(_daily_budget_key()) or 0.0)
        if spent >= settings.daily_budget_usd:
            raise HTTPException(status_code=402, detail="Daily budget exceeded")
    except HTTPException:
        raise
    except redis.RedisError as exc:
        logger.warning("Redis unavailable in check_budget: %s", exc)


def record_cost(input_tokens: int, output_tokens: int) -> float:
    """Gọi SAU khi gọi LLM. Cộng chi phí của request vào tổng, trả về chi phí request."""
    cost = (input_tokens / 1000.0) * PRICE_INPUT_PER_1K + (
        output_tokens / 1000.0
    ) * PRICE_OUTPUT_PER_1K
    if r is None:
        return cost
    try:
        key = _daily_budget_key()
        r.incrbyfloat(key, cost)
        r.expire(key, 86400 * 2)
    except redis.RedisError as exc:
        logger.warning("Redis unavailable in record_cost: %s", exc)
    return cost
