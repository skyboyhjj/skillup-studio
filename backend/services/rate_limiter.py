"""每日限额服务 — 基于 Redis 的终端限流

每个终端（按 IP 识别）每天限制：
- URL 提取：5 次
- 文字提取：5 次
"""
import datetime
from typing import Optional

import redis.asyncio as aioredis

from config import REDIS_URL

# 每日限额
DAILY_LIMIT_URL = 5
DAILY_LIMIT_TEXT = 5

# Redis key 前缀
KEY_PREFIX = "rate_limit:extract"


async def _get_redis() -> Optional[aioredis.Redis]:
    """获取 Redis 连接（懒连接）"""
    try:
        client = aioredis.from_url(REDIS_URL, decode_responses=True, socket_connect_timeout=3)
        await client.ping()
        return client
    except Exception:
        return None


def _get_client_ip(request) -> str:
    """从请求中提取客户端真实 IP"""
    # 优先取 Nginx 转发的 X-Forwarded-For
    forwarded = request.headers.get("X-Forwarded-For", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    # 直接连接的 IP
    client = getattr(request, "client", None)
    if client and hasattr(client, "host"):
        return client.host
    return "unknown"


def _today_key(extract_type: str, ip: str) -> str:
    """生成当天的限流 key"""
    today = datetime.date.today().isoformat()
    return f"{KEY_PREFIX}:{extract_type}:{ip}:{today}"


def _seconds_until_midnight() -> int:
    """计算距离当天午夜的秒数"""
    now = datetime.datetime.now()
    tomorrow = now.replace(hour=0, minute=0, second=0, microsecond=0) + datetime.timedelta(days=1)
    return int((tomorrow - now).total_seconds())


async def check_and_increment(request, extract_type: str) -> tuple[bool, int, int]:
    """检查是否超过每日限额，未超则递增。

    Args:
        request: FastAPI Request 对象
        extract_type: "url" 或 "text"

    Returns:
        (allowed: bool, current: int, limit: int)
    """
    limit = DAILY_LIMIT_URL if extract_type == "url" else DAILY_LIMIT_TEXT
    ip = _get_client_ip(request)
    key = _today_key(extract_type, ip)

    redis = await _get_redis()
    if redis is None:
        # Redis 不可用时放行（降级策略）
        return True, 0, limit

    try:
        current = await redis.get(key)
        if current is None:
            # 首次请求，设值并设 TTL 到午夜
            current = 0
        current = int(current)

        if current >= limit:
            await redis.close()
            return False, current, limit

        # 原子递增
        new_val = await redis.incr(key)
        # 设置 TTL（只在首次创建时设置）
        if new_val == 1:
            await redis.expire(key, _seconds_until_midnight())

        await redis.close()
        return True, new_val, limit

    except Exception:
        # Redis 异常时降级放行
        return True, 0, limit


async def get_remaining(request, extract_type: str) -> int:
    """查询剩余次数（不递增）"""
    limit = DAILY_LIMIT_URL if extract_type == "url" else DAILY_LIMIT_TEXT
    ip = _get_client_ip(request)
    key = _today_key(extract_type, ip)

    redis = await _get_redis()
    if redis is None:
        return limit

    try:
        current = await redis.get(key)
        await redis.close()
        if current is None:
            return limit
        return max(0, limit - int(current))
    except Exception:
        return limit