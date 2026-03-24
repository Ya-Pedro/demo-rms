\
\
\
\
\
\
\
\
\
   
import asyncio
import os
import sys
from logging.config import fileConfig
from pathlib import Path

from sqlalchemy import pool, engine_from_config
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

                                                                           
                                                                          
BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

                                                                             
from database import Base              
import models                                                                      

                                                                            
config = context.config

                                       
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

                                                                                 
target_metadata = Base.metadata

                                                                             
def _get_sync_url() -> str:
\
\
\
\
\
\
\
\
       
    raw_url = os.environ.get("DATABASE_URL", "sqlite+aiosqlite:///./rms_demo.db")

    if raw_url.startswith("postgresql+asyncpg://"):
        return raw_url.replace("postgresql+asyncpg://", "postgresql+psycopg2://", 1)
    elif raw_url.startswith("asyncpg://"):
        return raw_url.replace("asyncpg://", "postgresql+psycopg2://", 1)
    elif raw_url.startswith("sqlite+aiosqlite://"):
        return raw_url.replace("sqlite+aiosqlite://", "sqlite://", 1)

                                               
    return raw_url

def _get_async_url() -> str:
                                                              
    return os.environ.get("DATABASE_URL", "sqlite+aiosqlite:///./rms_demo.db")

                                                                                
                                                             
                                                     
                                                                                
def run_migrations_offline() -> None:
\
\
\
\
\
\
\
\
       
    url = _get_sync_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
                                                                                      
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()

                                                                                
                                                   
                               
                                                                                
def do_run_migrations(connection: Connection) -> None:
                                                                           
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()

async def run_async_migrations() -> None:
\
\
\
\
       
    connectable = async_engine_from_config(
        {"sqlalchemy.url": _get_async_url()},
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,                                                        
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()

def run_migrations_online() -> None:
                                                                      
    asyncio.run(run_async_migrations())

                                                                               
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()