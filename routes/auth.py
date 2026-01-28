import os
from datetime import datetime,timezone,timedelta
from fastapi import APIRouter,HTTPException,Request,Response
from bson import ObjectId
from app.db import get_db
from models.auth import SignUpRequest,SignInRequest,TokenOut
from app.auth.security import (
    hash_password,
    verify_password,
    generate_refresh_token,
    hash_refresh_token,
)
from app.auth.jwt import create_access_token


router = APIRouter(prefix="/auth",tags=["auth"])

REFRESH_COOKIE_NAME = "refresh_token"
REFRESH_COOKIE_PATH = "/api/v1/auth"

def cookie_secure() -> bool:
    return os.getenv("COOKIE_SECURE", "false").lower() == "true"

def refresh_expires_days() -> int:
    return int(os.getenv("REFRESH_TOKEN_EXPIRES_DAYS","14"))

@router.post("/signup",response_model=TokenOut)
async def signup(data: SignUpRequest , request: Request,response: Response):
    db = get_db(request)
    existing = await db.users.find_one({"email": data.email.lower()})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    doc = {
        "name": data.name,
        "email": data.email.lower(),
        "password_hash": hash_password(data.password),
        "age": data.age,
        "created_at": datetime.now(timezone.utc)
    }
    result = await db.users.insert_one(doc)
    user_id = str(result.inserted_id)

    refresh_token = generate_refresh_token()
    refresh_token_hash = hash_refresh_token(refresh_token)

    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(days=refresh_expires_days())

    db.sessions.insert_one({
        "user_id": ObjectId(user_id),
        "refresh_hash": refresh_token_hash,
        "created_at": now,
        "expires_at": expires_at,
        "revoked_at": None,
        "revoked_from": None
    })

    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=refresh_token,
        httponly=True,
        secure=cookie_secure(),
        samesite="lax",
        path=REFRESH_COOKIE_PATH,
        max_age=refresh_expires_days() * 24 * 60 * 60,
    )

    access = create_access_token(subject=user_id)
    return TokenOut(access_token=access)


@router.post("/signin", response_model=TokenOut)
async def signin(data: SignInRequest, request: Request, response: Response):
    db = get_db(request)

    user = await db.users.find_one({"email": data.email})

    if not user:
        raise HTTPException(status_code=401,detail="Invalid credentials")
    
    if not verify_password(data.password,user["password_hash"]):
        raise HTTPException(status_code=401,detail="Invalid Credentials")

    
    user_id = str(user["_id"])

    refresh_token = generate_refresh_token()
    refresh_token_hash = hash_refresh_token(refresh_token)
    
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(days=refresh_expires_days())

    db.sessions.insert_one({
        "user_id": ObjectId(user_id),
        "refresh_hash": refresh_token_hash,
        "created_at": now,
        "expires_at": expires_at,
        "revoked_at": None,
        "revoked_from": None
    })

    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=refresh_token,
        httponly=True,
        secure=cookie_secure(),
        samesite="lax",
        path=REFRESH_COOKIE_PATH,
        max_age=refresh_expires_days() * 24 * 60 * 60,
    )

    access = create_access_token(subject=user_id)
    return TokenOut(access_token=access)


@router.post("/refresh", response_model=TokenOut)
async def refresh(request: Request, response: Response):
    db = get_db(request)
    token = request.cookies.get(REFRESH_COOKIE_NAME)
    if not token:
        raise HTTPException(status_code=401, detail="Missing refresh token")

    token_hash = hash_refresh_token(token)
    now = datetime.now(timezone.utc)

    session = await db.sessions.find_one({"refresh_hash": token_hash})
    if not session:
        # reuse detection idea: token not found -> treat as invalid
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    if session.get("revoked_at") is not None:
        # refresh token reuse detected (already revoked)
        # aggressive response: revoke all sessions for that user
        await db.sessions.update_many(
            {"user_id": session["user_id"], "revoked_at": None},
            {"$set": {"revoked_at": now}}
        )
        raise HTTPException(status_code=401, detail="Refresh token reuse detected. Signed out.")

    #convert session["expires_at"] to utc timezone
    session["expires_at"] = session["expires_at"].replace(tzinfo=timezone.utc)

    if session["expires_at"] < now:
        # expired session
        await db.sessions.update_one({"_id": session["_id"]}, {"$set": {"revoked_at": now}})
        raise HTTPException(status_code=401, detail="Refresh token expired")

    # rotate refresh token: revoke old + create new
    new_refresh = generate_refresh_token()
    new_hash = hash_refresh_token(new_refresh)
    expires_at = now + timedelta(days=refresh_expires_days())

    await db.sessions.update_one({"_id": session["_id"]}, {"$set": {"revoked_at": now}})
    await db.sessions.insert_one({
        "user_id": session["user_id"],
        "refresh_hash": new_hash,
        "created_at": now,
        "expires_at": expires_at,
        "revoked_at": None,
        "rotated_from": session["_id"],
    })

    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=new_refresh,
        httponly=True,
        secure=cookie_secure(),
        samesite="lax",
        path=REFRESH_COOKIE_PATH,
        max_age=refresh_expires_days() * 24 * 60 * 60,
    )

    access = create_access_token(subject=str(session["user_id"]))
    return TokenOut(access_token=access)


@router.post("/signout")
async def signout(request: Request, response: Response):
    db = get_db(request)
    token = request.cookies.get(REFRESH_COOKIE_NAME)

    if token:
        token_hash = hash_refresh_token(token)
        now = datetime.now(timezone.utc)
        await db.sessions.update_one(
            {"refresh_hash": token_hash, "revoked_at": None},
            {"$set": {"revoked_at": now}}
        )

    response.delete_cookie(key=REFRESH_COOKIE_NAME, path=REFRESH_COOKIE_PATH)
    return {"message": "Signed out"}

