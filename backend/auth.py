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
                                                                  
                                                       
ACCESS_TOKEN_EXPIRE_MINUTES = max(5, int(os.environ.get("ACCESS_TOKEN_EXPIRE_MINUTES", 15)))

                                                                                
                                                                         
                                                        
@lru_cache(maxsize=1)
def _get_redis() -> "_redis_sync.Redis":
                                                                              
                                                        
    import os as _os
    _redis_url = _os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    return _redis_sync.from_url(_redis_url, decode_responses=True, socket_connect_timeout=2)

REDIS_SESSION_KEY = "active_session:{user_id}"
                                                                  
                                                                      
SESSION_TTL_SECONDS = ACCESS_TOKEN_EXPIRE_MINUTES * 60 + 60

def set_active_session(user_id: int, session_id: str) -> None:
                                                                             
    try:
        r = _get_redis()
        key = REDIS_SESSION_KEY.format(user_id=user_id)
        r.set(key, session_id, ex=SESSION_TTL_SECONDS)
    except Exception:
                                                         
        import logging
        logging.getLogger(__name__).warning(
            "Redis недоступен: set_active_session user_id=%s", user_id
        )

def get_active_session(user_id: int) -> str | None:
                                                                   
    try:
        r = _get_redis()
        key = REDIS_SESSION_KEY.format(user_id=user_id)
        return r.get(key)
    except Exception:
        import logging
        logging.getLogger(__name__).warning(
            "Redis недоступен: get_active_session user_id=%s", user_id
        )
                                                                    
                                                                                  
        return None

                                                                                
                                                         
                                                                      
 
                                                                                              
                                                                              
                                                                               
 
                                                                
                                                                                            

import time as _time
from threading import Lock as _Lock

SESSION_CACHE_TTL = 30                                          
_session_cache: dict[int, tuple[str, float]] = {}
_session_cache_lock = _Lock()

def _check_session_cached(user_id: int, token_session_id: str) -> bool:
\
\
\
\
\
       
    now = _time.monotonic()

    with _session_cache_lock:
        cached = _session_cache.get(user_id)
        if cached is not None:
            cached_sid, checked_at = cached
            if now - checked_at < SESSION_CACHE_TTL:
                                                               
                return cached_sid == token_session_id

                                                
    active_sid = get_active_session(user_id)

    if active_sid is None:
                                                                        
                                                                          
        return True

                   
    with _session_cache_lock:
        _session_cache[user_id] = (active_sid, now)

    return active_sid == token_session_id

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