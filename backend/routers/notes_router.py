from __future__ import annotations
from typing import Optional, List
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database import get_db
from models import Note, User, UserRole
from schemas import NoteResponse, NoteUpdateRequest
from auth import get_current_user

router = APIRouter(prefix="/notes", tags=["Заметки"])

def get_scope_for_user(user: User) -> str:
    user_role = str(user.role).lower()
    if user_role in [
        UserRole.SUPERADMIN.value,
        UserRole.ADMIN.value,
        "userrole.superadmin",
        "userrole.admin",
        "superadmin",
        "admin",
    ]:
        return "admin_shared"
    return f"user_{user.id}"

@router.get("", response_model=NoteResponse)
async def get_notes(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    scope = get_scope_for_user(current_user)
    stmt = (
        select(Note)
        .where(Note.scope == scope)
        .options(selectinload(Note.updated_by))
    )
    result = await db.execute(stmt)
    note = result.scalar_one_or_none()

    if not note:
        return NoteResponse(
            scope=scope,
            sheets=[],
            updated_at=None,
            updated_by_name=None
        )

    return NoteResponse(
        scope=note.scope,
        sheets=note.data if isinstance(note.data, list) else [],
        updated_at=note.updated_at,
        updated_by_name=note.updated_by.full_name if note.updated_by else None
    )

@router.put("", response_model=NoteResponse)
async def update_notes(
    body: NoteUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    scope = get_scope_for_user(current_user)
    stmt = (
        select(Note)
        .where(Note.scope == scope)
        .options(selectinload(Note.updated_by))
    )
    result = await db.execute(stmt)
    note = result.scalar_one_or_none()

    if not note:
        note = Note(
            scope=scope,
            data=body.sheets,
            updated_by_id=current_user.id
        )
        db.add(note)
    else:
        note.data = body.sheets
        note.updated_by_id = current_user.id
        note.updated_at = func.now()

    await db.commit()
    await db.refresh(note)

    return NoteResponse(
        scope=note.scope,
        sheets=note.data if isinstance(note.data, list) else [],
        updated_at=note.updated_at,
        updated_by_name=current_user.full_name
    )
