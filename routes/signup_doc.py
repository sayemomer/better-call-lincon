import os
import json
from datetime import datetime, timezone
from fastapi import APIRouter, UploadFile, File, BackgroundTasks, Request, HTTPException
from bson import ObjectId
from app.ai.signup_agent import run_signup_extraction_crew

router = APIRouter(prefix="/auth", tags=["Auth-Doc"])

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

async def process_signup_job(app, job_id: str):
    if not ObjectId.is_valid(job_id):
        return

    client = getattr(app.state, "mongo_client", None)
    if client is None:
        return

    db_name = getattr(app.state, "db_name", "fastapi_crud")
    db = client[db_name]

    job = await db.signup_jobs.find_one({"_id": ObjectId(job_id)})
    if not job:
        return

    await db.signup_jobs.update_one(
        {"_id": ObjectId(job_id)},
        {"$set": {"status": "extracting", "updated_at": datetime.now(timezone.utc)}}
    )

    try:
        file_path = job["file_path"]

        output = run_signup_extraction_crew(file_path)
        if isinstance(output, str):
            output = json.loads(output)

        await db.signup_jobs.update_one(
            {"_id": ObjectId(job_id)},
            {"$set": {
                "status": output["status"],
                "extracted": output["fields"],
                "reason": output.get("reason"),
                "updated_at": datetime.now(timezone.utc),
            }}
        )
        

    except Exception as e:
        await db.signup_jobs.update_one(
            {"_id": ObjectId(job_id)},
            {"$set": {
                "status": "failed",
                "error": str(e),
                "updated_at": datetime.now(timezone.utc),
            }}
        )

@router.post("/signup-doc")
async def signup_doc(request: Request, background: BackgroundTasks, file: UploadFile = File(...)):
    if file.content_type not in ["application/pdf", "image/png", "image/jpeg"]:
        raise HTTPException(status_code=400, detail="Upload PDF or PNG/JPEG image")

    safe_name = os.path.basename(file.filename).replace(" ", "_")
    filename = f"{int(datetime.now().timestamp())}_{safe_name}"
    file_path = os.path.join(UPLOAD_DIR, filename)

    with open(file_path, "wb") as f:
        f.write(await file.read())

    client = getattr(request.app.state, "mongo_client", None)
    if client is None:
        raise HTTPException(status_code=500, detail="MongoDB not connected")

    db = client[getattr(request.app.state, "db_name", "fastapi_crud")]
    now = datetime.now(timezone.utc)

    result = await db.signup_jobs.insert_one({
        "status": "queued",
        "file_path": file_path,
        "extracted": None,
        "reason": None,
        "error": None,
        "created_at": now,
        "updated_at": now,
    })

    job_id = str(result.inserted_id)

    # pass app, not request
    background.add_task(process_signup_job, request.app, job_id)

    return {"job_id": job_id, "status": "queued"}

@router.get("/signup-doc/{job_id}")
async def signup_doc_status(request: Request, job_id: str):
    if not ObjectId.is_valid(job_id):
        raise HTTPException(status_code=400, detail="Invalid job id")

    client = getattr(request.app.state, "mongo_client", None)
    if client is None:
        raise HTTPException(status_code=500, detail="MongoDB not connected")

    db = client[getattr(request.app.state, "db_name", "fastapi_crud")]
    job = await db.signup_jobs.find_one({"_id": ObjectId(job_id)})
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return {
        "job_id": job_id,
        "status": job["status"],
        "extracted": job.get("extracted"),
        "reason": job.get("reason"),
        "error": job.get("error"),
    }
