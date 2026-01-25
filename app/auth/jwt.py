import os
from datetime import datetime,timedelta,timezone
from jose import jwt,JWTError


def create_access_token(subject: str) -> str:
    secret = os.getenv("JWT_SECRET","dev_secret_change_me")
    alg = os.getenv("JWT_ALG","HS256")
    exp_min = int(os.getenv("ACCESS_TOKEN_EXPIRE_MIN", "60"))  # minutes; default 1h

    now = datetime.now(timezone.utc)

    payload = {
        "sub": subject,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=exp_min)).timestamp())
    }
 
    return jwt.encode(payload,secret,algorithm=alg)



def decode_access_token(token:str) -> dict:
    secret= os.getenv("JWT_SECRET", "dev_secret_change_me")
    alg = os.getenv("JWT_ALG","HS256")

    try:
        return jwt.decode(token,secret,algorithms=[alg])
    except JWTError as e:
        raise ValueError("Invalid token")