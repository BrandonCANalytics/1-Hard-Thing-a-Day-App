# utils/ip_utils.py
import os, hmac, hashlib

_SECRET = os.getenv("IP_HASH_SECRET", "dev-secret-change-me").encode("utf-8")

def hash_ip(ip: str | None) -> str | None:
    if not ip:
        return None
    return hmac.new(_SECRET, ip.encode("utf-8"), hashlib.sha256).hexdigest()
