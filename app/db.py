from motor.motor_asyncio import AsyncIOMotorClient
from fastapi import Request

MONGO_URL = "mongodb://localhost:27017"
DB_NAME = "fastapi_crud"

client : AsyncIOMotorClient | None = None

def connect_to_mongo(app, mongo_url:str):
    app.state.mongo_client = AsyncIOMotorClient(mongo_url)


def close_mongo_connection(app):
    client = getattr(app.state, "mongo_client", None)
    if client:
        client.close()

    

def get_db(request: Request):
    client = getattr(request.app.state, "mongo_client", None)
    if client is None:
        raise RuntimeError("MongoDB not connected")
    db_name = getattr(request.app.state, "db_name", DB_NAME)
    return client[db_name]