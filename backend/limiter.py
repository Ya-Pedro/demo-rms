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
   
import os
import logging

from slowapi import Limiter
from slowapi.util import get_remote_address

logger = logging.getLogger(__name__)

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
ENV       = os.environ.get("ENV", "production")

def _make_limiter() -> Limiter:
\
\
\
       
    return Limiter(
        key_func=get_remote_address,
        storage_uri=REDIS_URL,
        default_limits=[],
                                                                                       
                                                                                          
        headers_enabled=False,
    )

                                                             
limiter = _make_limiter()