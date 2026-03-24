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
\
\
\
\
   
import re
import os
import hmac
import hashlib
import time
import secrets
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database import get_db
from models import User
from schemas import (
    LoginRequest, Token, UserResponse,
    ChangePasswordRequest, ForgotPasswordRequest, ChangeOwnPasswordRequest,
    TwoFactorVerifyRequest, TwoFactorSetupResponse,
    TwoFactorConfirmRequest, TwoFactorDisableRequest,
)
from auth import (
    verify_password, create_access_token, get_current_user,
    get_password_hash, generate_random_password,
    set_active_session, _invalidate_session_cache,
)
from email_service import send_password_reset_email
from limiter import limiter
from services.totp import generate_totp_secret, get_totp_uri, generate_qr_svg, verify_totp_code

router = APIRouter(prefix="/auth", tags=["Аутентификация"])

                                                                                
                                                                  
                                            
_TEMP_TOKEN_SECRET = os.environ.get("SECRET_KEY", "dev-secret-key")
_TEMP_TOKEN_TTL = 300           

def _create_temp_token(user_id: int) -> str:
    ts = int(time.time())
    payload = f"{user_id}:{ts}"
    sig = hmac.new(_TEMP_TOKEN_SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return f"{payload}:{sig}"

def _verify_temp_token(token: str) -> int | None:
                                                                       
    try:
        parts = token.split(":")
        if len(parts) != 3:
            return None
        user_id_str, ts_str, sig = parts
        payload = f"{user_id_str}:{ts_str}"
        expected_sig = hmac.new(_TEMP_TOKEN_SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, expected_sig):
            return None
        if int(time.time()) - int(ts_str) > _TEMP_TOKEN_TTL:
            return None
        return int(user_id_str)
    except Exception:
        return None

def validate_password_strength(password: str) -> str | None:
\
\
\
\
\
\
\
\
       
    if len(password) < 8:
        return "Пароль должен быть не менее 8 символов"
    if not re.search(r'[A-ZА-ЯЁ]', password):
        return "Пароль должен содержать хотя бы одну заглавную букву"
    if not re.search(r'[!@#$%^&*()\-_=+\[\]{}|;:\'",.<>?/\\`~]', password):
        return "Пароль должен содержать хотя бы один спецсимвол (!@#$% и др.)"
    return None

def _get_client_ip(request: Request) -> str:
\
\
\
\
\
\
\
\
       
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()
    return request.client.host if request.client else "unknown"

@router.post("/login")
@limiter.limit("10/5minute")
async def login(
    login_data: LoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
\
\
\
\
\
\
\
       
    result = await db.execute(
        select(User).where(User.email == login_data.email)
    )
    user = result.scalar_one_or_none()

    if not user or not verify_password(login_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный email или пароль",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Пользователь деактивирован"
        )

                                                                               
    if user.is_2fa_enabled:
        temp_token = _create_temp_token(user.id)
        return {
            "requires_2fa": True,
            "temp_token": temp_token,
        }

                                                                               
    return await _issue_tokens(db, user, request)

@router.post("/2fa/verify")
@limiter.limit("10/5minute")
async def verify_2fa(
    data: TwoFactorVerifyRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
\
\
\
\
       
    user_id = _verify_temp_token(data.temp_token)
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Временный токен недействителен или истёк. Войдите заново.",
        )

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Пользователь не найден")

    if not verify_totp_code(user.totp_secret, data.code):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный код двухфакторной аутентификации",
        )

    return await _issue_tokens(db, user, request)

async def _issue_tokens(db: AsyncSession, user: User, request: Request) -> dict:
\
\
\
\
\
\
\
\
\
       
    import secrets as _secrets
    from datetime import timedelta
    from services.refresh_token import create_refresh_token, revoke_all_user_tokens, ACCESS_TOKEN_EXPIRE_MINUTES as RT_EXPIRE
    client_ip = _get_client_ip(request)

                                                                                
    await revoke_all_user_tokens(db, user.id)

                                                                               
                                                                
                                                                               
    session_id = _secrets.token_hex(16)                                
    set_active_session(user.id, session_id)
    _invalidate_session_cache(user.id)                                    
    access_token = create_access_token(
        data={"sub": user.email, "role": user.role.value, "sid": session_id},
        expires_delta=timedelta(minutes=RT_EXPIRE),
    )
    refresh_token_val = await create_refresh_token(db, user.id, ip=client_ip)
    return {
        "access_token": access_token,
        "refresh_token": refresh_token_val,
        "token_type": "bearer",
        "is_temporary_password": bool(user.is_temporary_password),
        "requires_2fa": False,
    }

                                                                              

                                                    
_TOTP_SETUP_TTL = 600

def _get_redis_client():
                                                                       
    import redis as _redis
    from limiter import REDIS_URL
    return _redis.from_url(REDIS_URL, decode_responses=True)

@router.get("/2fa/setup", response_model=TwoFactorSetupResponse)
async def setup_2fa(
    current_user: User = Depends(get_current_user),
):
\
\
\
\
\
\
\
       
    secret = generate_totp_secret()
    setup_id = secrets.token_hex(32)

                                             
    try:
        r = _get_redis_client()
        r.setex(f"totp_setup:{current_user.id}:{setup_id}", _TOTP_SETUP_TTL, secret)
    except Exception:
                                                                                 
        import logging as _log
        _log.getLogger(__name__).warning(
            "Redis недоступен для хранения TOTP-секрета. Секрет возвращается клиенту (небезопасно в prod)."
        )
        uri = get_totp_uri(secret, current_user.email)
        qr_svg = generate_qr_svg(secret, current_user.email)
        return TwoFactorSetupResponse(secret=secret, qr_svg=qr_svg, uri=uri, setup_id=setup_id)

    uri = get_totp_uri(secret, current_user.email)
    qr_svg = generate_qr_svg(secret, current_user.email)
                                                                        
    return TwoFactorSetupResponse(secret="", qr_svg=qr_svg, uri=uri, setup_id=setup_id)

class TwoFactorConfirmWithSecretRequest(TwoFactorConfirmRequest):
    secret: str = ""
    setup_id: str = ""

@router.post("/2fa/confirm")
@router.post("/2fa/activate")
async def activate_2fa(
    data: TwoFactorConfirmWithSecretRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
\
\
\
\
       
    secret = None

                                                        
    if data.setup_id:
        try:
            r = _get_redis_client()
            redis_key = f"totp_setup:{current_user.id}:{data.setup_id}"
            secret = r.get(redis_key)
            if secret:
                r.delete(redis_key)                               
        except Exception:
            pass

                                                             
    if not secret and data.secret:
        secret = data.secret

    if not secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Сессия настройки 2FA истекла. Начните настройку заново.",
        )

    if not verify_totp_code(secret, data.code):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Неверный код. Убедитесь что аутентификатор настроен правильно.",
        )
    current_user.totp_secret = secret
    current_user.is_2fa_enabled = True
    await db.commit()
    return {"message": "Двухфакторная аутентификация активирована"}

@router.post("/2fa/disable")
async def disable_2fa(
    data: TwoFactorDisableRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
\
\
       
    if not current_user.is_2fa_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="2FA не активирована",
        )
    if not verify_totp_code(current_user.totp_secret, data.code):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Неверный код двухфакторной аутентификации",
        )
    current_user.totp_secret = None
    current_user.is_2fa_enabled = False
    await db.commit()
    return {"message": "Двухфакторная аутентификация отключена"}

@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
                               
    return current_user

@router.post("/change-password")
async def change_password(
    data: ChangePasswordRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
\
\
\
       
    if data.new_password != data.confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Пароли не совпадают"
        )

    pwd_error = validate_password_strength(data.new_password)
    if pwd_error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=pwd_error
        )

    current_user.hashed_password = get_password_hash(data.new_password)
    current_user.is_temporary_password = False
    await db.commit()

    return {"message": "Пароль успешно изменён"}

@router.post("/change-own-password")
async def change_own_password(
    data: ChangeOwnPasswordRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
                                                               
    if not verify_password(data.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Неверный текущий пароль"
        )

    if data.new_password != data.confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Пароли не совпадают"
        )

    pwd_error = validate_password_strength(data.new_password)
    if pwd_error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=pwd_error
        )

    current_user.hashed_password = get_password_hash(data.new_password)
    current_user.is_temporary_password = False
    await db.commit()

    return {"message": "Пароль успешно изменён"}

@router.post("/forgot-password")
@limiter.limit("5/15minute")
async def forgot_password(
    data: ForgotPasswordRequest,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
\
\
\
\
\
       
    result = await db.execute(
        select(User).where(User.email == data.email)
    )
    user = result.scalar_one_or_none()

    if user and user.is_active:
        new_password = generate_random_password()
        user.hashed_password = get_password_hash(new_password)
        user.is_temporary_password = True
        await db.commit()

        await send_password_reset_email(
            email=data.email,
            full_name=user.full_name,
            password=new_password
        )

    return {"message": "Если email зарегистрирован, новый пароль отправлен на почту"}

                                                                               
                         
                                                                               
from services.refresh_token import (
    create_refresh_token, validate_refresh_token,
    revoke_refresh_token, revoke_all_user_tokens,
    ACCESS_TOKEN_EXPIRE_MINUTES as RT_ACCESS_EXPIRE,
)
from datetime import timedelta
from pydantic import BaseModel as _BaseModel

class RefreshRequest(_BaseModel):
    refresh_token: str

@router.post("/refresh")
async def refresh_access_token(
    data: RefreshRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
\
\
\
\
\
\
       
    token_obj = await validate_refresh_token(db, data.refresh_token)
    if not token_obj:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh-токен недействителен или истёк",
        )

    result = await db.execute(select(User).where(User.id == token_obj.user_id))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Пользователь деактивирован",
        )

                                                   
    await revoke_refresh_token(db, data.refresh_token)

                               
    new_access_token = create_access_token(
        data={"sub": user.email, "role": user.role.value},
        expires_delta=timedelta(minutes=RT_ACCESS_EXPIRE),
    )

                                
    client_ip = _get_client_ip(request)
    new_refresh_token = await create_refresh_token(db, user.id, ip=client_ip)

    return {
        "access_token": new_access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer",
    }

@router.post("/logout")
async def logout(
    data: RefreshRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
                                                
    await revoke_refresh_token(db, data.refresh_token)
    return {"message": "Выход выполнен"}

@router.post("/logout-all")
async def logout_all(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
                                                    
    count = await revoke_all_user_tokens(db, current_user.id)
    return {"message": f"Все сессии завершены ({count})"}