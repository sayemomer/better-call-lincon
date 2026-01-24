import collections
from fastapi import FastAPI, Depends
from app.db import connect_to_mongo, close_mongo_connection, get_db
from routes.users import router as users_router
from routes.auth import router as auth_router
from routes.signup_doc import router as signup_doc_router
from routes.profile import router as profile_router
from routes.documents import router as documents_router
from dotenv import load_dotenv
import os
from app.auth.deps import get_current_user
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

app = FastAPI(
    docs_url="/api/v1/docs",
    redoc_url="/api/v1/redoc",
    openapi_url="/api/v1/openapi.json"     
)

app.include_router(profile_router, prefix="/api/v1", dependencies=[Depends(get_current_user)])
app.include_router(documents_router, prefix="/api/v1", dependencies=[Depends(get_current_user)])
app.include_router(users_router, prefix="/api/v1", dependencies=[Depends(get_current_user)])
app.include_router(auth_router, prefix="/api/v1")
app.include_router(signup_doc_router , prefix="/api/v1")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    mongo_url = os.getenv("MONGO_URL","mongodb://localhost:27017")
    app.state.db_name = os.getenv("DB_NAME","fastapi_crud")
    connect_to_mongo(app, mongo_url)

@app.on_event("shutdown")
async def shutdown_event():
    close_mongo_connection(app)

@app.get("/me")
async def me(user: dict = Depends(get_current_user)):
    return user

@app.get("/health")
async def health():
    return { "status": "ok"}