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
\
   
from __future__ import annotations

import os
import logging
import pyotp
import qrcode
import qrcode.image.svg
import io
import base64

logger = logging.getLogger(__name__)

                                                                         
TOTP_ISSUER = os.environ.get("TOTP_ISSUER", "RMS")

def generate_totp_secret() -> str:
                                                            
    return pyotp.random_base32()

def get_totp_uri(secret: str, email: str) -> str:
\
\
\
       
    totp = pyotp.TOTP(secret)
    return totp.provisioning_uri(name=email, issuer_name=TOTP_ISSUER)

def generate_qr_svg(secret: str, email: str) -> str:
\
\
\
       
    uri = get_totp_uri(secret, email)
    factory = qrcode.image.svg.SvgPathImage
    img = qrcode.make(uri, image_factory=factory, box_size=10)
    buf = io.BytesIO()
    img.save(buf)
    return buf.getvalue().decode("utf-8")

def verify_totp_code(secret: str, code: str) -> bool:
\
\
\
\
       
    if not secret or not code:
        return False
    try:
        totp = pyotp.TOTP(secret)
        return totp.verify(code.strip(), valid_window=1)
    except Exception as e:
        logger.warning(f"TOTP verify error: {e}")
        return False
