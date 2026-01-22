from fastapi import Depends,HTTPException,Request
from fastapi.security import HTTPAuthorizationCredentials,HTTPBearer
from bson import ObjectId
from app.db import get_db
from app.auth.jwt import decode_access_token

bearer = HTTPBearer(auto_error=False)

async def get_current_user(
    request:Request,
    creds: HTTPAuthorizationCredentials = Depends(bearer)
):

    if creds is None or creds.scheme.lower() != "bearer":
        raise HTTPException(status_code=401,detail="Missing access token")

    try:
        payload = decode_access_token(creds.credentials)
        user_id = payload.get("sub")

    except Exception:
        raise HTTPException(status_code=401, detail="Invalid access token")


    if not user_id or not ObjectId.is_valid(user_id):
        raise HTTPException(status_code=401,detail="Invalid access token subject")
    
    db = get_db(request)
    user = await db.users.find_one({"_id": ObjectId(user_id)})

    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return {
        "id": str(user["_id"]),
        "name": user["name"],
        "email": user["email"],
        "age": user.get("age", 0)      
    }