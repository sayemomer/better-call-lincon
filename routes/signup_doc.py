import os
import json
from datetime import datetime, timezone, timedelta, date
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, BackgroundTasks, Request, HTTPException, Response, Body
from bson import ObjectId
from pydantic import BaseModel, EmailStr, Field
from app.ai.signup_agent import run_signup_extraction_crew
from app.auth.security import hash_password, generate_refresh_token, hash_refresh_token
from app.auth.jwt import create_access_token
from app.db import get_db

router = APIRouter(prefix="/auth", tags=["Auth-Doc"])

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

REFRESH_COOKIE_NAME = "refresh_token"

def cookie_secure() -> bool:
    return os.getenv("COOKIE_SECURE", "false").lower() == "true"

def refresh_expires_days() -> int:
    return int(os.getenv("REFRESH_TOKEN_EXPIRES_DAYS", "14"))

class FinalizeSignupRequest(BaseModel):
    job_id: str
    email: EmailStr
    password: str = Field(..., min_length=8)

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

        print(output)

        if isinstance(output, str):
            output = json.loads(output)

        await db.signup_jobs.update_one(
            {"_id": ObjectId(job_id)},
            {"$set": {
                "status": output["status"],
                "extracted": output["fields"],
                "reason": output.get("reason"),
                "ocr_markdown": output.get("ocr_markdown"),
                "ocr_extracted": output.get("ocr_extracted"),
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
    """
    Upload a passport document for signup.
    The AI agent will:
    1. Validate that the document is a passport (returns error if not)
    2. Extract name, email (if present), and age from passport
    3. If email is missing, status will be 'need_review' - user must provide email/password via /finalize endpoint
    4. If all fields present, status will be 'completed' - but user still needs to provide email/password for account creation
    """
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

    status = job["status"]
    extracted = job.get("extracted") or {}
    ocr_markdown = job.get("ocr_markdown")
    ocr_extracted = job.get("ocr_extracted")
    
    # Safety check: If status is "completed" but email is missing, correct it to "need_review"
    # This handles edge cases where the agent might have returned "completed" incorrectly
    email = (extracted.get("email") or "").strip()
    if status == "completed" and not email:
        status = "need_review"
        # Update the database to reflect the correct status
        await db.signup_jobs.update_one(
            {"_id": ObjectId(job_id)},
            {"$set": {"status": "need_review"}}
        )
    
    # Determine if email/password is needed
    # Email/password is needed when status is 'need_review' (user must provide to complete signup)
    needs_email_password = status == "need_review"
    
    # If document is invalid, this is an error
    is_error = status == "invalid_document"

    return {
        "job_id": job_id,
        "status": status,
        "extracted": extracted,
        "reason": job.get("reason"),
        "error": job.get("error"),
        "needs_email_password": needs_email_password,
        "is_error": is_error,
        "ocr_markdown": ocr_markdown,
        "ocr_extracted": ocr_extracted,
    }

@router.post("/signup-doc/finalize")
async def finalize_signup(
    request: Request,
    response: Response,
    data: FinalizeSignupRequest = Body(...)
):
    """
    Finalize signup by providing email and password when status is 'need_review'.
    Creates the user account, creates/updates the profile with ALL extracted passport data,
    and returns access token.
    
    Profile fields extracted from passport:
    - Basic: surname, given_name, name, dob, citizenship, sex, place_of_birth
    - Passport: passport_number, country_code, personal_number, previous_passport_no
    - Dates: date_of_issue, date_of_expiry
    - Family: fathers_name, mothers_name, marital_status
    - Address: permanent_address
    - Travel: travel_history (JSON array)
    - Age: Calculated from DOB (also stored in user model)
    """
    if not ObjectId.is_valid(data.job_id):
        raise HTTPException(status_code=400, detail="Invalid job id")

    db = get_db(request)
    
    # Get the signup job
    job = await db.signup_jobs.find_one({"_id": ObjectId(data.job_id)})
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    status = job.get("status")
    if status == "invalid_document":
        raise HTTPException(
            status_code=400,
            detail=f"Cannot finalize signup. Document is not a passport. {job.get('reason', '')}"
        )
    
    if status != "need_review":
        raise HTTPException(
            status_code=400, 
            detail=f"Cannot finalize signup. Job status is '{status}', expected 'need_review'. Please check the document status first."
        )
    
    extracted = job.get("extracted") or {}
    name = extracted.get("name")
    surname = extracted.get("surname")
    given_name = extracted.get("given_name")
    age = extracted.get("age")
    
    if not name:
        raise HTTPException(status_code=400, detail="Name is required but not found in passport")
    
    # Check if email already exists
    existing = await db.users.find_one({"email": data.email.lower()})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create user account
    now = datetime.now(timezone.utc)
    user_doc = {
        "name": name,
        "email": data.email.lower(),
        "password_hash": hash_password(data.password),
        "age": age,
        "created_at": now,
        "signup_job_id": ObjectId(data.job_id),  # Link to signup job
    }
    
    result = await db.users.insert_one(user_doc)
    user_id = str(result.inserted_id)
    user_id_obj = ObjectId(user_id)
    
    # Update signup job status
    await db.signup_jobs.update_one(
        {"_id": ObjectId(data.job_id)},
        {"$set": {
            "status": "completed",
            "user_id": user_id_obj,
            "updated_at": now,
        }}
    )
    
    # Create a document record for the passport used during signup
    # This allows it to show up in the documents list and CRS status
    if job.get("file_path"):
        file_path = job["file_path"]
        # Try to determine mime type from file extension
        mime_type = "application/pdf"
        if file_path.lower().endswith((".png", ".jpg", ".jpeg")):
            mime_type = f"image/{file_path.split('.')[-1].lower()}"
        
        passport_document = {
            "user_id": user_id_obj,
            "filename": os.path.basename(file_path),
            "mime_type": mime_type,
            "storage_url": file_path,
            "type_detected": "passport",  # We know it's a passport from signup validation
            "created_at": now,
        }
        await db.documents.insert_one(passport_document)
    
    # Helper function to parse date strings and convert to datetime for MongoDB
    def parse_date_str(date_str):
        if not date_str:
            return None
        try:
            # Parse as date first, then convert to datetime at midnight UTC
            date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
            return datetime.combine(date_obj, datetime.min.time(), tzinfo=timezone.utc)
        except (ValueError, TypeError):
            return None
    
    # Create or update profile with ALL extracted passport data
    profile_data = {
        "user_id": user_id_obj,
        "status": "incomplete",  # Profile is incomplete until more documents are uploaded
        "updated_at": now,
    }
    
    # Basic identification
    if surname:
        profile_data["surname"] = surname
    if given_name:
        profile_data["given_name"] = given_name
    
    dob_str = extracted.get("dob")
    if dob_str:
        dob = parse_date_str(dob_str)
        if dob:
            profile_data["dob"] = dob
    
    citizenship = extracted.get("citizenship")
    if citizenship:
        profile_data["citizenship"] = citizenship
    
    sex = extracted.get("sex")
    if sex:
        profile_data["sex"] = sex
    
    place_of_birth = extracted.get("place_of_birth")
    if place_of_birth:
        profile_data["place_of_birth"] = place_of_birth
    
    # Passport details
    passport_number = extracted.get("passport_number")
    if passport_number:
        profile_data["passport_number"] = passport_number
    
    country_code = extracted.get("country_code")
    if country_code:
        profile_data["country_code"] = country_code
    
    personal_number = extracted.get("personal_number")
    if personal_number:
        profile_data["personal_number"] = personal_number
    
    previous_passport_no = extracted.get("previous_passport_no")
    if previous_passport_no:
        profile_data["previous_passport_no"] = previous_passport_no
    
    date_of_issue_str = extracted.get("date_of_issue")
    if date_of_issue_str:
        date_of_issue = parse_date_str(date_of_issue_str)
        if date_of_issue:
            profile_data["date_of_issue"] = date_of_issue
    
    date_of_expiry_str = extracted.get("date_of_expiry")
    if date_of_expiry_str:
        date_of_expiry = parse_date_str(date_of_expiry_str)
        if date_of_expiry:
            profile_data["date_of_expiry"] = date_of_expiry
    
    # Family information
    fathers_name = extracted.get("fathers_name")
    if fathers_name:
        profile_data["fathers_name"] = fathers_name
    
    mothers_name = extracted.get("mothers_name")
    if mothers_name:
        profile_data["mothers_name"] = mothers_name
    
    marital_status = extracted.get("marital_status")
    if marital_status:
        profile_data["marital_status"] = marital_status
    
    # Address
    permanent_address = extracted.get("permanent_address")
    if permanent_address:
        profile_data["permanent_address"] = permanent_address
    
    # Travel history
    travel_history = extracted.get("travel_history")
    if travel_history and isinstance(travel_history, list):
        profile_data["travel_history"] = travel_history
    
    # Check if profile already exists
    existing_profile = await db.profiles.find_one({"user_id": user_id_obj})
    
    if existing_profile:
        # Update existing profile with passport data
        await db.profiles.update_one(
            {"user_id": user_id_obj},
            {"$set": profile_data}
        )
    else:
        # Create new profile
        profile_data["created_at"] = now
        await db.profiles.insert_one(profile_data)
    
    # Create session with refresh token
    refresh_token = generate_refresh_token()
    refresh_token_hash = hash_refresh_token(refresh_token)
    expires_at = now + timedelta(days=refresh_expires_days())
    
    await db.sessions.insert_one({
        "user_id": ObjectId(user_id),
        "refresh_hash": refresh_token_hash,
        "created_at": now,
        "expires_at": expires_at,
        "revoked_at": None,
        "revoked_from": None
    })
    
    # Set refresh token cookie
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=refresh_token,
        httponly=True,
        secure=cookie_secure(),
        samesite="lax",
        path="/auth",
        max_age=refresh_expires_days() * 24 * 60 * 60,
    )
    
    # Generate access token
    access_token = create_access_token(subject=user_id)
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user_id": user_id,
        "message": "Signup completed successfully"
    }
