import hashlib
import hmac
import os
import secrets
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["argon2"],deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str , password_hash: str)-> bool:
    return pwd_context.verify(password,password_hash)

def generate_refresh_token() -> str:
    return secrets.token_urlsafe(64)

def hash_refresh_token(token: str) -> str:
    secret = os.getenv("JWT_SECRET","dev_secret_change_me").encode("utf-8")
    return hmac.new(secret, token.encode("utf-8"),hashlib.sha256).hexdigest()
