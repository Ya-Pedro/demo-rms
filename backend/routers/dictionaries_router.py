\
\
\
   
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional

from database import get_db
from models import User, Dictionary, DictionaryType, UserRole
from schemas import DictionaryCreate, DictionaryUpdate, DictionaryResponse, DictionaryListResponse
from auth import get_current_user, get_current_active_admin

router = APIRouter(prefix="/dictionaries", tags=["Справочники"])

@router.get("", response_model=DictionaryListResponse)
async def get_dictionaries(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    type: Optional[DictionaryType] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    is_active: Optional[bool] = None,
):
                                                   
    query = select(Dictionary)
    count_query = select(func.count(Dictionary.id))

    if type:
        query = query.where(Dictionary.type == type)
        count_query = count_query.where(Dictionary.type == type)

    if is_active is not None:
        query = query.where(Dictionary.is_active == is_active)
        count_query = count_query.where(Dictionary.is_active == is_active)

    total_result = await db.execute(count_query)
    total = total_result.scalar()

    query = query.order_by(Dictionary.sort_order, Dictionary.id).offset(skip).limit(limit)
    result = await db.execute(query)
    items = result.scalars().all()

    return DictionaryListResponse(items=items, total=total)

@router.get("/by-type/{dict_type}", response_model=list[DictionaryResponse])
async def get_dictionaries_by_type(
    dict_type: DictionaryType,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
                                                                             
    query = (
        select(Dictionary)
        .where(Dictionary.type == dict_type, Dictionary.is_active == True)
        .order_by(Dictionary.sort_order, Dictionary.id)
    )
    result = await db.execute(query)
    return result.scalars().all()

@router.post("", response_model=DictionaryResponse, status_code=status.HTTP_201_CREATED)
async def create_dictionary(
    data: DictionaryCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_admin),
):
                                                   
    item = Dictionary(
        type=data.type,
        value=data.value,
        description=data.description,
        sort_order=data.sort_order,
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return item

@router.get("/{item_id}", response_model=DictionaryResponse)
async def get_dictionary(
    item_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
                                          
    result = await db.execute(select(Dictionary).where(Dictionary.id == item_id))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Элемент справочника не найден")
    return item

@router.patch("/{item_id}", response_model=DictionaryResponse)
async def update_dictionary(
    item_id: int,
    data: DictionaryUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_admin),
):
                                             
    result = await db.execute(select(Dictionary).where(Dictionary.id == item_id))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Элемент справочника не найден")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(item, field, value)

    await db.commit()
    await db.refresh(item)
    return item

@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_dictionary(
    item_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_admin),
):
                                                 
    result = await db.execute(select(Dictionary).where(Dictionary.id == item_id))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Элемент справочника не найден")

    item.is_active = False
    await db.commit()
