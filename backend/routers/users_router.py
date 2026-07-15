\
\
\
   
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from typing import Optional

from database import get_db
from models import User, UserRole
from schemas import UserCreate, UserCreateWithPassword, UserUpdate, UserResponse, UserListResponse, CompleteTourRequest
from auth import get_current_user, get_current_active_admin, get_password_hash, generate_random_password
from email_service import send_welcome_email

router = APIRouter(prefix="/users", tags=["Пользователи"])

@router.get("", response_model=UserListResponse)
async def get_users(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    role: Optional[UserRole] = None
):
\
\
\
\
\
\
       
    query = select(User)
    count_query = select(func.count(User.id))
    
                                       
    
    if search:
        search_filter = f"%{search}%"
        query = query.where(
            (User.email.ilike(search_filter)) | 
            (User.full_name.ilike(search_filter))
        )
        count_query = count_query.where(
            (User.email.ilike(search_filter)) | 
            (User.full_name.ilike(search_filter))
        )
    
    if role:
        query = query.where(User.role == role)
        count_query = count_query.where(User.role == role)
    
                     
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
               
    query = query.order_by(User.id).offset(skip).limit(limit)
    result = await db.execute(query)
    users = result.scalars().all()
    
    return UserListResponse(items=users, total=total)

@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: UserCreateWithPassword,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_admin)
):
\
\
\
\
\
\
\
       
                                                                                                    
    if current_user.role == UserRole.RECRUITER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав для создания пользователей"
        )
    
                                    
    if current_user.role == UserRole.ADMIN and user_data.role == UserRole.SUPERADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Администратор не может создавать суперадминистраторов"
        )
    
                                   
    existing = await db.execute(
        select(User).where(User.email == user_data.email)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Пользователь с таким email уже существует"
        )
    
                                                  
    if user_data.password and len(user_data.password) >= 6:
        password = user_data.password
    else:
        password = generate_random_password()
    
    hashed_password = get_password_hash(password)
    
                 
    new_user = User(
        email=user_data.email,
        full_name=user_data.full_name,
        role=user_data.role,
        hashed_password=hashed_password,
        is_temporary_password=True
    )
    
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    
                                         
    await send_welcome_email(
        email=user_data.email,
        full_name=user_data.full_name,
        password=password
    )
    
    return new_user

@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_admin)
):
                        
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь не найден"
        )
    
                                  
    if current_user.role == UserRole.ADMIN and user.role == UserRole.SUPERADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Нет доступа к этому пользователю"
        )
    
    return user

@router.patch("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user_data: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_admin)
):
                     
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь не найден"
        )
    
                                  
    if current_user.role == UserRole.ADMIN and user.role == UserRole.SUPERADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Нет доступа к этому пользователю"
        )
    
                                        
    if current_user.role == UserRole.ADMIN and user_data.role == UserRole.SUPERADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Администратор не может назначать роль суперадминистратора"
        )
    
                                 
    update_data = user_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(user, field, value)
    
    await db.commit()
    await db.refresh(user)
    
    return user

@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_admin)
):
\
\
\
       
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь не найден"
        )
    
    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Нельзя удалить самого себя"
        )
    
                                    
    if current_user.role == UserRole.ADMIN and user.role == UserRole.SUPERADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Нет прав на удаление суперадминистратора"
        )
    
    try:
        await db.delete(user)
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Нельзя удалить пользователя, у которого есть активные вакансии. Сначала передайте их другому рекрутеру."
        )

                                                                                

@router.post("/complete-tour", response_model=UserResponse)
async def complete_tour(
    data: CompleteTourRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
\
\
\
\
\
\
\
\
       
    if data.tour == "vacancies":
        current_user.is_vacancies_tour_completed = True
    elif data.tour == "reports":
        current_user.is_reports_tour_completed = True
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Допустимые значения tour: 'vacancies' | 'reports'",
        )

    await db.commit()
    await db.refresh(current_user)
    return current_user