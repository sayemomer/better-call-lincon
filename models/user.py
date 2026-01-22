from pydantic import BaseModel,EmailStr,Field
from typing import Optional

class UserBase(BaseModel):
    name: str = Field(..., min_length=2)
    email: EmailStr
    age: int = Field(..., ge=0)

class UserCreate(UserBase):
    pass

class UserUpdate(UserBase):
    name: Optional[str]
    email: Optional[EmailStr]
    age: Optional[int]



class UserOut(UserBase):
    id: str
    class Config:
        from_attributes = True


def user_entity(user: dict) -> dict:
    return {
        "id": str(user["_id"]),
        "name": user["name"],
        "email": user["email"],
        "age": user["age"],
    }