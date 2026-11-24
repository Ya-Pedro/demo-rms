\
\
   
from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import os
import secrets
import string

from database import get_db
from models import User, UserRole
import redis as _redis_sync
from functools import lru_cache

                                                                               
_DEFAULT_SECRET = "rms-super-secret-key-change-in-production-2024"
SECRET_KEY = os.environ.get("SECRET_KEY", _DEFAULT_SECRET)

                                                                 
                                                                
                              
_allow_default = os.environ.get("RMS_ALLOW_DEFAULT_SECRET", "0") == "1"
if SECRET_KEY == _DEFAULT_SECRET and not _allow_default:
    import logging as _log
    _log.getLogger(__name__).critical(
        "БЕЗОПАСНОСТЬ: SECRET_KEY не задан или совпадает с дефолтным значением! "
        "Сгенерируйте ключ командой: openssl rand -hex 32 "
        "и запишите его в переменную окружения SECRET_KEY. "
        "Для локальной разработки установите RMS_ALLOW_DEFAULT_SECRET=1"
    )
                                                 
    if os.environ.get("ENV", "production") != "development":
        raise RuntimeError(
            "SECRET_KEY не настроен. "
            "Установите переменную окружения SECRET_KEY или RMS_ALLOW_DEFAULT_SECRET=1 для dev."
        )

ALGORITHM = "HS256"
# Время жизни access токена (по умолчанию 12 часов, минимум 60 минут)
ACCESS_TOKEN_EXPIRE_MINUTES = max(60, int(os.environ.get("ACCESS_TOKEN_EXPIRE_MINUTES", 720)))

# ---------------------------------------------------------------------------
# Redis: Хранение активных сессий пользователя (поддержка мультисессий / вкладок)
# ---------------------------------------------------------------------------
@lru_cache(maxsize=1)
def _get_redis() -> "_redis_sync.Redis":
    import os as _os
    _redis_url = _os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    return _redis_sync.from_url(_redis_url, decode_responses=True, socket_connect_timeout=2)

REDIS_SESSIONS_KEY = "active_sessions:{user_id}"
REDIS_SESSION_KEY  = "active_session:{user_id}"  # для обратной совместимости
SESSION_TTL_SECONDS = ACCESS_TOKEN_EXPIRE_MINUTES * 60 + 86400  # запас +24ч

import time as _time
from threading import Lock as _Lock

SESSION_CACHE_TTL = 30
_session_cache: dict[int, tuple[set[str], float]] = {}
_session_cache_lock = _Lock()

def add_active_session(user_id: int, session_id: str) -> None:
    """Добавляет session_id в список активных сессий пользователя (не удаляя другие вкладки)."""
    try:
        r = _get_redis()
        key = REDIS_SESSIONS_KEY.format(user_id=user_id)
        pipe = r.pipeline()
        pipe.sadd(key, session_id)
        pipe.expire(key, SESSION_TTL_SECONDS)
        pipe.execute()
    except Exception:
        import logging
        logging.getLogger(__name__).warning("Redis недоступен: add_active_session user_id=%s", user_id)

    try:
        with _session_cache_lock:
            cached = _session_cache.get(user_id)
            if cached is not None:
                cached[0].add(session_id)
            else:
                _session_cache[user_id] = ({session_id}, _time.monotonic())
    except Exception:
        pass

def set_active_session(user_id: int, session_id: str) -> None:
    """Псевдоним add_active_session для совместимости со старыми вызовами."""
    add_active_session(user_id, session_id)

def remove_active_session(user_id: int, session_id: str) -> None:
    """Удаляет конкретную сессию (например, при одиночном logout)."""
    try:
        r = _get_redis()
        key = REDIS_SESSIONS_KEY.format(user_id=user_id)
        r.srem(key, session_id)
    except Exception:
        pass
    try:
        with _session_cache_lock:
            cached = _session_cache.get(user_id)
            if cached is not None:
                cached[0].discard(session_id)
    except Exception:
        pass

def clear_all_active_sessions(user_id: int) -> None:
    """Удаляет все активные сессии пользователя (при logout-all)."""
    try:
        r = _get_redis()
        r.delete(REDIS_SESSIONS_KEY.format(user_id=user_id))
        r.delete(REDIS_SESSION_KEY.format(user_id=user_id))
    except Exception:
        pass
    try:
        with _session_cache_lock:
            _session_cache.pop(user_id, None)
    except Exception:
        pass

def get_active_session(user_id: int) -> str | None:
    """Совместимость: возвращает любую активную сессию или None."""
    try:
        r = _get_redis()
        members = r.smembers(REDIS_SESSIONS_KEY.format(user_id=user_id))
        if members:
            return next(iter(members))
        return r.get(REDIS_SESSION_KEY.format(user_id=user_id))
    except Exception:
        return None

def _check_session_cached(user_id: int, token_session_id: str) -> bool:
    """
    Проверяет, действительна ли сессия токена.
    Поддерживает одновременную работу в нескольких вкладках.
    При сбое Redis или отсутствии ключа не разлогинивает пользователя (fail-open).
    """
    now = _time.monotonic()

    # 1. Проверяем локальный кэш процесса
    with _session_cache_lock:
        cached = _session_cache.get(user_id)
        if cached is not None:
            cached_sids, checked_at = cached
            if now - checked_at < SESSION_CACHE_TTL and token_session_id in cached_sids:
                return True

    # 2. Проверяем Redis
    try:
        r = _get_redis()
        key = REDIS_SESSIONS_KEY.format(user_id=user_id)

        # Проверяем в множестве активных сессий
        if r.sismember(key, token_session_id):
            with _session_cache_lock:
                cached = _session_cache.get(user_id)
                if cached is not None:
                    cached[0].add(token_session_id)
                else:
                    _session_cache[user_id] = ({token_session_id}, now)
            return True

        # Обратная совместимость со старым строковым ключом
        old_sid = r.get(REDIS_SESSION_KEY.format(user_id=user_id))
        if old_sid and old_sid == token_session_id:
            r.sadd(key, token_session_id)
            r.expire(key, SESSION_TTL_SECONDS)
            with _session_cache_lock:
                _session_cache[user_id] = ({token_session_id}, now)
            return True

        # Если ключ существует в Redis, обновляем локальный кэш актуальными сессиями
        if r.exists(key):
            current_members = set(r.smembers(key))
            with _session_cache_lock:
                _session_cache[user_id] = (current_members, now)
            return token_session_id in current_members

        # Ключа нет (все сессии были завершены через logout-all)
        with _session_cache_lock:
            _session_cache[user_id] = (set(), now)
        return False

    except Exception as e:
        import logging
        logging.getLogger(__name__).warning("Redis session check fallback (allowing request): %s", e)
        return True

def _invalidate_session_cache(user_id: int) -> None:
    with _session_cache_lock:
        _session_cache.pop(user_id, None)

                  
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

                     
security = HTTPBearer()

def verify_password(plain_password: str, hashed_password: str) -> bool:
                                            
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
                         
    return pwd_context.hash(password)

def generate_random_password(length: int = 12) -> str:
                                                  
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
\
\
\
\
\
\
       
    import secrets as _secrets
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    now = datetime.now(timezone.utc)
    to_encode.update({
        "exp": expire,
        "iat": now,
    })
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
\
\
\
\
\
\
\
\
\
       
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Не удалось подтвердить учетные данные",
        headers={"WWW-Authenticate": "Bearer"},
    )
    session_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Сессия завершена. Выполните вход заново.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        token = credentials.credentials
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if user is None:
        raise credentials_exception
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Пользователь деактивирован"
        )

                                                                               
                                             
                                                                             
    token_sid = payload.get("sid")
    if token_sid is not None:
        if not _check_session_cached(user.id, token_sid):
            raise session_exception

    return user

async def get_current_active_admin(
    current_user: User = Depends(get_current_user)
) -> User:
                                              
    if current_user.role not in [UserRole.ADMIN, UserRole.SUPERADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав доступа"
        )
    return current_user

async def get_current_superadmin(
    current_user: User = Depends(get_current_user)
) -> User:
                                     
    if current_user.role != UserRole.SUPERADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Требуются права суперадминистратора"
        )
    return current_user