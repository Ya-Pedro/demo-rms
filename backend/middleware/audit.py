\
\
\
   
from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import Optional, Any

from fastapi import Request, Response
from sqlalchemy import Column, Integer, String, DateTime, Text, JSON
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.middleware.base import BaseHTTPMiddleware

from database import Base

logger = logging.getLogger("rms.audit")

                                                                                

class AuditLog(Base):
                                                  
    __tablename__ = "audit_log"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    user_id = Column(Integer, nullable=True, index=True)
    user_email = Column(String(255), nullable=True)
    user_role = Column(String(50), nullable=True)
    action = Column(String(100), nullable=False, index=True)                                     
    resource = Column(String(100), nullable=True)                                    
    resource_id = Column(String(50), nullable=True)
    method = Column(String(10), nullable=True)
    path = Column(String(500), nullable=True)
    status_code = Column(Integer, nullable=True)
    ip_address = Column(String(50), nullable=True)
    details = Column(JSON, nullable=True)                                               
    duration_ms = Column(Integer, nullable=True)

                                                                                

class AuditService:
                                                                             

    def __init__(self, db: AsyncSession):
        self.db = db

    async def log(
        self,
        action: str,
        *,
        user_id: Optional[int] = None,
        user_email: Optional[str] = None,
        user_role: Optional[str] = None,
        resource: Optional[str] = None,
        resource_id: Optional[Any] = None,
        method: Optional[str] = None,
        path: Optional[str] = None,
        status_code: Optional[int] = None,
        ip_address: Optional[str] = None,
        details: Optional[dict] = None,
        duration_ms: Optional[int] = None,
    ) -> None:
        entry = AuditLog(
            action=action,
            user_id=user_id,
            user_email=user_email,
            user_role=user_role,
            resource=resource,
            resource_id=str(resource_id) if resource_id is not None else None,
            method=method,
            path=path,
            status_code=status_code,
            ip_address=ip_address,
            details=details,
            duration_ms=duration_ms,
        )
        self.db.add(entry)
        await self.db.commit()

        logger.info(
            "AUDIT | action=%-30s user=%-30s ip=%-15s status=%s path=%s",
            action,
            user_email or "-",
            ip_address or "-",
            status_code or "-",
            path or "-",
        )

                                                                                 

                                                                                 
_AUDIT_PATHS = {
    ("POST", "/api/auth/login"),
    ("POST", "/api/auth/forgot-password"),
    ("POST", "/api/auth/change-password"),
    ("POST", "/api/auth/change-own-password"),
    ("POST", "/api/vacancies/import"),
    ("POST", "/api/export"),
    ("POST", "/api/export/vacancies/smart"),
}

_RESOURCE_MAP = {
    "/api/vacancies": "vacancy",
    "/api/users": "user",
    "/api/dictionaries": "dictionary",
    "/api/auth": "auth",
    "/api/export": "export",
}

def _get_client_ip(request: Request) -> str:
                                                                             
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()
    return request.client.host if request.client else "unknown"

def _get_resource(path: str) -> str:
    for prefix, resource in _RESOURCE_MAP.items():
        if path.startswith(prefix):
            return resource
    return "unknown"

def _get_action(method: str, path: str, status_code: int) -> Optional[str]:
                                                                                   
    if path == "/api/auth/login":
        return "LOGIN_SUCCESS" if status_code < 400 else "LOGIN_FAILED"
    if path == "/api/auth/forgot-password":
        return "PASSWORD_RESET_REQUESTED"
    if path in ("/api/auth/change-password", "/api/auth/change-own-password"):
        return "PASSWORD_CHANGED" if status_code < 400 else None
    if "/api/vacancies/import" in path:
        return "VACANCY_IMPORT" if status_code < 400 else "VACANCY_IMPORT_FAILED"
    if "/api/export" in path:
        return "DATA_EXPORT" if status_code < 400 else None
                    
    if path.startswith("/api/vacancies"):
        crud = {"POST": "VACANCY_CREATE", "PATCH": "VACANCY_UPDATE",
                "DELETE": "VACANCY_DELETE"}.get(method)
        if crud and status_code < 400:
            return crud
                
    if path.startswith("/api/users"):
        crud = {"POST": "USER_CREATE", "PATCH": "USER_UPDATE",
                "DELETE": "USER_DELETE"}.get(method)
        if crud and status_code < 400:
            return crud
    return None

class AuditMiddleware(BaseHTTPMiddleware):
\
\
\
\
       

    async def dispatch(self, request: Request, call_next):
        start = time.perf_counter()
        response: Response = await call_next(request)
        duration_ms = int((time.perf_counter() - start) * 1000)

        method = request.method
        path = request.url.path

        action = _get_action(method, path, response.status_code)
        if action is None:
            return response

        user = getattr(request.state, "current_user", None)
        ip = _get_client_ip(request)

                                             
        logger.info(
            "AUDIT | action=%-30s user=%-30s ip=%-15s status=%s path=%s duration=%dms",
            action,
            getattr(user, "email", "anonymous"),
            ip,
            response.status_code,
            path,
            duration_ms,
        )

                                                                           
        from database import AsyncSessionLocal
        async def _write_to_db():
            try:
                async with AsyncSessionLocal() as db:
                    entry = AuditLog(
                        action=action,
                        user_id=getattr(user, "id", None),
                        user_email=getattr(user, "email", None),
                        user_role=getattr(user, "role", None) and getattr(user.role, "value", str(user.role)),
                        method=method,
                        path=path,
                        status_code=response.status_code,
                        ip_address=ip,
                        duration_ms=duration_ms,
                        resource=_get_resource(path),
                    )
                    db.add(entry)
                    await db.commit()
            except Exception as exc:
                logger.warning("Не удалось записать audit_log в БД: %s", exc)

        import asyncio
        asyncio.ensure_future(_write_to_db())

        return response