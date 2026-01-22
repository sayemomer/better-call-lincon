from fastapi import APIRouter, HTTPException, Request
from bson import ObjectId
from app.db import get_db
from models.user import UserCreate, UserUpdate, UserOut, user_entity


router = APIRouter(tags=["users"])

@router.post("/", response_model=UserOut)
async def create_user(user: UserCreate, request: Request):
    db = get_db(request)
    result = await db.users.insert_one(user.dict())
    new_user = await db.users.find_one({"_id": result.inserted_id})
    return user_entity(new_user)


@router.get("/{user_id}", response_model=UserOut)
async def get_user(user_id: str, request: Request):
    db = get_db(request)

    if not ObjectId.is_valid(user_id):
        raise HTTPException(status_code=400, detail="Invalid user ID")

    user = await db.users.find_one({"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user_entity(user)

@router.get("/", response_model=list[UserOut])
async def list_users(request: Request):
    db = get_db(request)
    users = []
    async for user in db.users.find():
        users.append(user_entity(user))
    return users

@router.put("/{user_id}", response_model=UserOut)
async def update_user(user_id: str, user: UserUpdate, request: Request):
    db = get_db(request)
    if not ObjectId.is_valid(user_id):
        raise HTTPException(status_code=400, detail="Invalid user ID")
    result = await db.users.update_one({"_id": ObjectId(user_id)}, {"$set": user.dict()})
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    return user_entity(await db.users.find_one({"_id": ObjectId(user_id)}))

@router.delete("/{user_id}")
async def delete_user(user_id: str, request: Request):
    db = get_db(request)
    if not ObjectId.is_valid(user_id):
        raise HTTPException(status_code=400, detail="Invalid user ID")
    result = await db.users.delete_one({"_id": ObjectId(user_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    return {"message": "User deleted successfully"}