\
\
\
   
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
import os

                                                                        
                                             
DATABASE_URL = os.environ.get("DATABASE_URL", None)

if DATABASE_URL is None:
                                 
    DATABASE_URL = "sqlite+aiosqlite:///./rms_demo.db"
    print("[INFO] Using SQLite for demo. For production, set DATABASE_URL to PostgreSQL.")

                     
if DATABASE_URL.startswith("sqlite"):
    engine = create_async_engine(
        DATABASE_URL,
        echo=False,
        connect_args={"check_same_thread": False}
    )
else:
    engine = create_async_engine(
        DATABASE_URL,
        echo=False,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20
    )

                              
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

                       
Base = declarative_base()

async def get_db():
                                            
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

async def init_db():
                                    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
