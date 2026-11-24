\
\
\
\
\
\
\
\
\
\
\
   
import os
import logging
from fastapi import Request
from slowapi import Limiter

logger = logging.getLogger(__name__)

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
ENV       = os.environ.get("ENV", "production")

def get_real_client_ip(request: Request) -> str:
    """
    Извлекает реальный IP клиента с учетом OpenShift Router / reverse proxy.
    Проверяет X-Forwarded-For (первый IP), X-Real-IP и fallback на client.host.
    """
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        client_ip = forwarded.split(",")[0].strip()
        if client_ip:
            return client_ip
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()
    return request.client.host if request.client else "127.0.0.1"

def _make_limiter() -> Limiter:
    return Limiter(
        key_func=get_real_client_ip,
        storage_uri=REDIS_URL,
        default_limits=[],
        headers_enabled=False,
    )

limiter = _make_limiter()