\
\
\
   
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import os
import logging
from pathlib import Path
from dotenv import load_dotenv

from slowapi.errors import RateLimitExceeded
from starlette.requests import Request as StarletteRequest
from starlette.responses import JSONResponse

import hashlib
from typing import Optional, Any, Dict, Tuple
from starlette.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from models import User

from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
from redis import asyncio as aioredis

                            
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

                             
from database import init_db
from limiter import limiter, REDIS_URL, ENV
from middleware.audit import AuditMiddleware
from routers.auth_router import router as auth_router
from routers.users_router import router as users_router
from routers.dictionaries_router import router as dictionaries_router
from routers.vacancies_router import router as vacancies_router
from routers.reports_router import router as reports_router
from routers.export_router import router as export_router
from routers.delegation_router import router as delegation_router
from routers.dashboards_router import router as dashboards_router
from routers.notes_router import router as notes_router
from routers.notifications_router import router as notifications_router
from routers.integration_router import router as integration_router
from services.scheduler_service import WeeklyReminderScheduler
import services.scheduler_service as scheduler_module

                   
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def _check_redis() -> None:
\
\
\
\
       
    import redis as _redis_sync
    try:
        r = _redis_sync.from_url(REDIS_URL, socket_connect_timeout=3)
        r.ping()
        logger.info(f"Redis: соединение установлено ({REDIS_URL})")
    except Exception as e:
        if ENV == "production":
            raise RuntimeError(
                f"Redis недоступен ({REDIS_URL}): {e}. "
                "Rate limiting не будет работать. "
                "Запустите Redis или установите ENV=development для локальной разработки."
            ) from e
        else:
            logger.warning(
                f"Redis недоступен ({REDIS_URL}): {e}. "
                "В dev-режиме rate limiting работает in-memory (не шарится между воркерами)."
            )

def rms_key_builder(
    func,
    namespace: str = "",
    *,
    request: Optional[Request] = None,
    response: Optional[Response] = None,
    args: Tuple[Any, ...] = (),
    kwargs: Dict[str, Any] = None,
) -> str:
    clean_kwargs = {}
    user_role = ""
    for k, v in (kwargs or {}).items():
        if isinstance(v, User):
            user_role = str(v.role.value if hasattr(v.role, 'value') else v.role)
        elif not isinstance(v, (AsyncSession, Request, Response)):
            clean_kwargs[k] = v
    query_str = ""
    if request:
        qp = sorted((k, v) for k, v in request.query_params.multi_items() if k != "_t")
        query_str = "&".join(f"{k}={v}" for k, v in qp)
    raw = f"{func.__module__}:{func.__name__}:{user_role}:{query_str}:{sorted(str(x) for x in clean_kwargs.items())}"
    cache_key = hashlib.md5(raw.encode()).hexdigest()
    return f"{namespace}:{cache_key}"

@asynccontextmanager
async def lifespan(app: FastAPI):
                                      
    logger.info("Starting RMS application...")
    await _check_redis()
    
    # Initialize Redis Cache with custom key builder that ignores transient dependencies like db session
    redis_client = aioredis.from_url(REDIS_URL, encoding="utf8", decode_responses=False)
    FastAPICache.init(RedisBackend(redis_client), prefix="fastapi-cache", key_builder=rms_key_builder)
    logger.info("FastAPI cache initialized with Redis")
    
    await init_db()
    logger.info("Database initialized")
                                   
    # Initialize and start Weekly Reminder Scheduler (Friday 13:00 MSK)
    scheduler_module.scheduler_instance = WeeklyReminderScheduler(redis_client=redis_client)
    scheduler_module.scheduler_instance.start()

    yield

    # Shutdown scheduler
    if scheduler_module.scheduler_instance:
        scheduler_module.scheduler_instance.stop()
    logger.info("Shutting down RMS application...")

                            
APP_VERSION = os.environ.get("APP_VERSION", "v0.3.0")

app = FastAPI(
    title="RMS - Recruitment Management System",
    description="Внутренняя HR система для управления вакансиями",
    version=APP_VERSION,
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
    redoc_url="/api/redoc",
    lifespan=lifespan
)

                                                                                
                                                        
                                                                        
from prometheus_fastapi_instrumentator import Instrumentator

Instrumentator(
    should_group_status_codes=True,
    excluded_handlers=["/metrics"],
).instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)

                                                                               
                                                                     
app.state.limiter = limiter
                                                                 
async def _rate_limit_handler(request: StarletteRequest, exc: RateLimitExceeded) -> JSONResponse:
    retry_after = getattr(exc, "retry_after", 60)
    return JSONResponse(
        status_code=429,
        content={"detail": f"Слишком много запросов. Попробуйте через {retry_after} сек."},
        headers={"Retry-After": str(retry_after)},
    )

app.add_exception_handler(RateLimitExceeded, _rate_limit_handler)

                    
                                                                         
                                                      
                                                                                
_raw_origins = os.environ.get('CORS_ORIGINS', 'http://localhost:3000,http://localhost:5173')
cors_origins = [o.strip() for o in _raw_origins.split(',') if o.strip()]

if '*' in cors_origins:
    _env = os.environ.get('ENV', 'production')
    if _env == 'development':
                                                  
        logger.warning(
            "CORS: wildcard * обнаружен. В dev-режиме allow_credentials отключён. "
            "Для продакшна уберите * из CORS_ORIGINS."
        )
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=False,                                                     
            allow_methods=["*"],
            allow_headers=["*"],
        )
    else:
        raise RuntimeError(
            "CORS_ORIGINS содержит wildcard '*' — это несовместимо с allow_credentials=True. "
            "Укажите конкретные origins: CORS_ORIGINS=http://localhost:3000,https://your-domain.ru"
        )
else:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

                                  
app.include_router(auth_router, prefix="/api")
app.include_router(users_router, prefix="/api")
app.include_router(dictionaries_router, prefix="/api")
app.include_router(vacancies_router, prefix="/api")
app.include_router(reports_router, prefix="/api")
app.include_router(export_router, prefix="/api")
app.include_router(delegation_router, prefix="/api")
app.include_router(dashboards_router, prefix="/api")
app.include_router(notes_router, prefix="/api")
app.include_router(notifications_router, prefix="/api")
app.include_router(integration_router, prefix="/api")

                           
app.add_middleware(AuditMiddleware)

@app.get("/api")
async def root():
    return {
        "message": "RMS API работает",
        "version": APP_VERSION,
        "status": "ok"
    }

@app.get("/api/version")
async def get_version():
    return {
        "version": APP_VERSION,
        "status": "ok"
    }

@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "version": APP_VERSION
    }