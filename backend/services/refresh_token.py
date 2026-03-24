\
\
\
   
from __future__ import annotations

import secrets
import os
from datetime import datetime, timedelta, timezone

from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database import Base

REFRESH_TOKEN_EXPIRE_DAYS = max(1, int(os.environ.get("REFRESH_TOKEN_EXPIRE_DAYS", 7)))

                                                                                   
from auth import ACCESS_TOKEN_EXPIRE_MINUTES                                                       

class RefreshToken(Base):
                                                      
    __tablename__ = "refresh_tokens"

    id = Column(Integer, primary_key=True, index=True)
    token = Column(String(128), unique=True, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    revoked = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
                           
    created_from_ip = Column(String(50), nullable=True)

def generate_refresh_token() -> str:
                                                                                          
    return secrets.token_hex(64)

async def create_refresh_token(
    db: AsyncSession,
    user_id: int,
    ip: str | None = None,
) -> str:
                                                               
    token_value = generate_refresh_token()
    token = RefreshToken(
        token=token_value,
        user_id=user_id,
        expires_at=datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
        created_from_ip=ip,
    )
    db.add(token)
    await db.commit()
    return token_value

async def validate_refresh_token(
    db: AsyncSession,
    token_value: str,
) -> RefreshToken | None:
                                                                             
    result = await db.execute(
        select(RefreshToken).where(RefreshToken.token == token_value)
    )
    token = result.scalar_one_or_none()
    if token is None:
        return None
    if token.revoked:
        return None
    if token.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        return None
    return token

async def revoke_refresh_token(db: AsyncSession, token_value: str) -> bool:
                                                                             
    result = await db.execute(
        select(RefreshToken).where(RefreshToken.token == token_value)
    )
    token = result.scalar_one_or_none()
    if not token:
        return False
    token.revoked = True
    await db.commit()
    return True

async def revoke_all_user_tokens(db: AsyncSession, user_id: int) -> int:
                                                                           
    result = await db.execute(
        select(RefreshToken).where(
            RefreshToken.user_id == user_id,
            RefreshToken.revoked == False,
        )
    )
    tokens = result.scalars().all()
    for token in tokens:
        token.revoked = True
    await db.commit()
    return len(tokens)