import asyncio
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
from redis import asyncio as aioredis
from routers.dashboards_router import get_dashboard_metrics

async def main():
    redis_client = aioredis.from_url("redis://rms_redis:6379", encoding="utf8", decode_responses=False)
    FastAPICache.init(RedisBackend(redis_client), prefix="fastapi-cache")
    
    # Let's see what keys are in redis
    keys = await redis_client.keys("fastapi-cache:dashboards:*")
    print("Keys before clear:", keys)
    
    await FastAPICache.clear(namespace="dashboards")
    
    keys_after = await redis_client.keys("fastapi-cache:dashboards:*")
    print("Keys after clear:", keys_after)

asyncio.run(main())
