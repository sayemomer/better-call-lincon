import os
import asyncio
import logging
from datetime import datetime, timezone, date
from fastapi import APIRouter, HTTPException, UploadFile, File, BackgroundTasks, Request, Depends
from bson import ObjectId
from typing import List
from app.db import get_db
from app.auth.deps import get_current_user
from app.ai.immigration_agent import run_immigration_extraction_crew
from app.utils.document_recommendations import get_recommended_documents, detect_permit_type_from_documents
from app.utils.crs_requirements import analyze_crs_requirements, get_required_documents_for_crs
from models.document import DocumentOut, RecommendedDocument, document_entity

logger = logging.getLogger(__name__)

router = APIRouter(tags=["documents"])

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

async def process_document_extraction(app, document_id: str):
    """Background task to extract profile data from uploaded document"""
    logger.info(f"Starting document extraction for document_id: {document_id}")
    
    if not ObjectId.is_valid(document_id):
        logger.error(f"Invalid document_id: {document_id}")
        return

    client = getattr(app.state, "mongo_client", None)
    if client is None:
        logger.error("MongoDB client not available")
        return

    db_name = getattr(app.state, "db_name", "fastapi_crud")
    db = client[db_name]

    document = await db.documents.find_one({"_id": ObjectId(document_id)})
    if not document:
        logger.error(f"Document not found: {document_id}")
        return

    try:
        file_path = document["storage_url"]
        logger.info(f"Processing document: {file_path}")
        
        # Check if file exists
        if not os.path.exists(file_path):
            logger.error(f"File not found: {file_path}")
            await db.documents.update_one(
                {"_id": ObjectId(document_id)},
                {"$set": {"type_detected": "unknown", "processing_error": "File not found"}}
            )
            return
        
        # Extract data from document - run blocking operation in thread pool
        loop = asyncio.get_running_loop()
        extraction_result = await loop.run_in_executor(None, run_immigration_extraction_crew, file_path)

        print("extraction_result")
        print(extraction_result)
        
        if extraction_result.get("status") in ["completed", "partial"]:
            fields = extraction_result.get("fields", {})
            document_type = extraction_result.get("document_type", "unknown")
            
            # If document_type is unknown, try to infer from extracted fields
            if document_type == "unknown" or not document_type:
                # Check for language test type
                lang_test_type = fields.get("language_test_type")
                if lang_test_type:
                    lang_test_type_lower = lang_test_type.lower()
                    if "ielts" in lang_test_type_lower:
                        document_type = "ielts"
                    elif "celpip" in lang_test_type_lower:
                        document_type = "celpip"
                    elif "pte" in lang_test_type_lower:
                        document_type = "pte_core"
                    elif "tef" in lang_test_type_lower:
                        document_type = "tef_canada"
                    elif "tcf" in lang_test_type_lower:
                        document_type = "tcf_canada"
                    else:
                        document_type = "language_test"
                    logger.info(f"Inferred document type from language_test_type: {document_type}")
                
                # Check for education fields
                elif fields.get("education_level") or fields.get("education_level_detail"):
                    document_type = "degree"  # Default to degree if education found
                
                # Check for work experience fields
                elif fields.get("canadian_work_years") is not None or fields.get("foreign_work_years") is not None:
                    document_type = "work_reference"
        
        
            await db.documents.update_one(
                {"_id": ObjectId(document_id)},
                {"$set": {"type_detected": document_type}}
            )
            
            # Update profile with extracted data
            user_id = document["user_id"]
            profile = await db.profiles.find_one({"user_id": user_id})

            if profile:
                update_data = {}
                # Get existing profile.data or create new dict
                profile_data_dict = profile.get("data") or {}
                if not isinstance(profile_data_dict, dict):
                    profile_data_dict = {}
                
                # Remove legacy fields from data dict if they exist (they should be top-level on profile)
                # education_json, language_json, work_json should not be in data
                profile_data_dict.pop("education_json", None)
                profile_data_dict.pop("language_json", None)
                profile_data_dict.pop("work_json", None)
                
                # Update basic fields (use datetime for MongoDB; BSON doesn't support date)
                if fields.get("dob"):
                    try:
                        d = datetime.fromisoformat(fields["dob"]).date()
                        update_data["dob"] = datetime.combine(d, datetime.min.time(), tzinfo=timezone.utc)
                        # Also add to profile.data for CRS
                        profile_data_dict["dob"] = fields["dob"]
                    except Exception:
                        pass
                
                if fields.get("citizenship"):
                    update_data["citizenship"] = fields["citizenship"]
                    profile_data_dict["citizenship"] = fields["citizenship"]
                
                if fields.get("province"):
                    update_data["province"] = fields["province"]
                
                if fields.get("city"):
                    update_data["city"] = fields["city"]
                
                if fields.get("arrival_date"):
                    try:
                        d = datetime.fromisoformat(fields["arrival_date"]).date()
                        update_data["arrival_date"] = datetime.combine(d, datetime.min.time(), tzinfo=timezone.utc)
                    except Exception:
                        pass
                
                # CRS-specific fields -> profile.data
                if fields.get("marital_status"):
                    profile_data_dict["marital_status"] = fields["marital_status"]
                
                if fields.get("spouse_accompanying") is not None:
                    profile_data_dict["spouse_accompanying"] = fields["spouse_accompanying"]
                
                if fields.get("spouse_canadian_pr") is not None:
                    profile_data_dict["spouse_canadian_pr"] = fields["spouse_canadian_pr"]
                
                # Education CRS fields - store in both data (for CRS calculator) and education_json (for schema)
                education_data = {}
                if fields.get("education_level"):
                    profile_data_dict["education_level"] = fields["education_level"]
                    education_data["education_level"] = fields["education_level"]
                
                if fields.get("education_level_detail"):
                    profile_data_dict["education_level_detail"] = fields["education_level_detail"]
                    education_data["education_level_detail"] = fields["education_level_detail"]
                
                if fields.get("canadian_education") is not None:
                    profile_data_dict["canadian_education"] = fields["canadian_education"]
                    education_data["canadian_education"] = fields["canadian_education"]
                
                # Store education in education_json at top level (as schema expects)
                if education_data:
                    existing_edu = profile.get("education_json") or {}
                    if isinstance(existing_edu, dict):
                        existing_edu.update(education_data)
                        update_data["education_json"] = existing_edu
                    else:
                        update_data["education_json"] = education_data
                
                # Language CRS fields - structure as language_scores
                if fields.get("language_test_type") or any(fields.get(f"language_{skill}") is not None for skill in ["speaking", "listening", "reading", "writing"]):
                    lang_scores = profile_data_dict.get("language_scores", {})
                    if fields.get("language_test_type"):
                        lang_scores["test"] = fields["language_test_type"]
                    for skill in ["speaking", "listening", "reading", "writing"]:
                        val = fields.get(f"language_{skill}")
                        if val is not None:
                            lang_scores[skill] = val
                    profile_data_dict["language_scores"] = lang_scores
                    
                    # Also update legacy language_json field for backward compatibility
                    legacy_lang = {
                        "test_type": fields.get("language_test_type"),
                        "speaking": fields.get("language_speaking"),
                        "listening": fields.get("language_listening"),
                        "reading": fields.get("language_reading"),
                        "writing": fields.get("language_writing"),
                    }
                    # Remove None values
                    legacy_lang = {k: v for k, v in legacy_lang.items() if v is not None}
                    if legacy_lang:
                        existing_lang_json = profile.get("language_json") or {}
                        if isinstance(existing_lang_json, dict):
                            existing_lang_json.update(legacy_lang)
                            update_data["language_json"] = existing_lang_json
                        else:
                            update_data["language_json"] = legacy_lang
                        logger.info(f"Updated legacy language_json: {legacy_lang}")
                        logger.info(f"Setting update_data['language_json'] = {update_data.get('language_json')}")
                
                # Second language
                if fields.get("second_language_test_type") or any(fields.get(f"second_language_{skill}") is not None for skill in ["speaking", "listening", "reading", "writing"]):
                    s2lang = profile_data_dict.get("second_language_scores", {})
                    if fields.get("second_language_test_type"):
                        s2lang["test"] = fields["second_language_test_type"]
                    for skill in ["speaking", "listening", "reading", "writing"]:
                        val = fields.get(f"second_language_{skill}")
                        if val is not None:
                            s2lang[skill] = val
                    profile_data_dict["second_language_scores"] = s2lang
                    profile_data_dict["has_second_language"] = True
                
                # Work experience CRS fields
                if fields.get("canadian_work_years") is not None:
                    profile_data_dict["canadian_work_years"] = int(fields["canadian_work_years"])
                
                if fields.get("foreign_work_years") is not None:
                    profile_data_dict["foreign_work_years"] = int(fields["foreign_work_years"])
                
                # Additional CRS factors
                if fields.get("certificate_of_qualification") is not None:
                    profile_data_dict["certificate_of_qualification"] = fields["certificate_of_qualification"]
                
                if fields.get("provincial_nomination") is not None:
                    profile_data_dict["provincial_nomination"] = fields["provincial_nomination"]
                
                if fields.get("sibling_in_canada") is not None:
                    profile_data_dict["sibling_in_canada"] = fields["sibling_in_canada"]
                
                # Spouse CRS fields
                if fields.get("spouse_education_level"):
                    profile_data_dict["spouse_education_level"] = fields["spouse_education_level"]
                
                if fields.get("spouse_canadian_work_years") is not None:
                    profile_data_dict["spouse_canadian_work_years"] = int(fields["spouse_canadian_work_years"])
                
                if fields.get("spouse_language_test_type") or any(fields.get(f"spouse_language_{skill}") is not None for skill in ["speaking", "listening", "reading", "writing"]):
                    spouse_lang = profile_data_dict.get("spouse_language_scores", {})
                    if fields.get("spouse_language_test_type"):
                        spouse_lang["test"] = fields["spouse_language_test_type"]
                    for skill in ["speaking", "listening", "reading", "writing"]:
                        val = fields.get(f"spouse_language_{skill}")
                        if val is not None:
                            spouse_lang[skill] = val
                    profile_data_dict["spouse_language_scores"] = spouse_lang
                
                # Legacy JSON fields (merge with existing if present) - for backward compatibility
                if fields.get("education"):
                    # If we already set education_json from individual fields, merge with legacy education
                    if "education_json" in update_data and isinstance(update_data["education_json"], dict):
                        if isinstance(fields["education"], dict):
                            update_data["education_json"].update(fields["education"])
                        else:
                            # If legacy education is not a dict, replace with it
                            update_data["education_json"] = fields["education"]
                    else:
                        # No education_json set yet, use legacy education
                        existing_edu = profile.get("education_json") or {}
                        if isinstance(existing_edu, dict) and isinstance(fields["education"], dict):
                            existing_edu.update(fields["education"])
                            update_data["education_json"] = existing_edu
                        else:
                            update_data["education_json"] = fields["education"]
                
                # Legacy language_json field - update if we have language_tests (from OCR tool) OR if already set above
                if fields.get("language_tests") and "language_json" not in update_data:
                    existing_lang = profile.get("language_json") or {}
                    if isinstance(existing_lang, dict) and isinstance(fields["language_tests"], dict):
                        existing_lang.update(fields["language_tests"])
                        update_data["language_json"] = existing_lang
                    else:
                        update_data["language_json"] = fields["language_tests"]
                
                if fields.get("work_experience"):
                    existing_work = profile.get("work_json") or {}
                    if isinstance(existing_work, dict) and isinstance(fields["work_experience"], dict):
                        existing_work.update(fields["work_experience"])
                        update_data["work_json"] = existing_work
                    else:
                        update_data["work_json"] = fields["work_experience"]
                
                # Always update profile.data with CRS structure (even if empty, to ensure structure exists)
                update_data["data"] = profile_data_dict

                print("update_data")
                print(update_data)
                
                if update_data:
                    update_data["updated_at"] = datetime.now(timezone.utc)
                    result = await db.profiles.update_one(
                        {"user_id": user_id},
                        {"$set": update_data}
                    )

                else:
                    logger.info(f"No profile updates needed for user {user_id}")
            else:
                # Create profile if it doesn't exist
                profile_data = {
                    "user_id": user_id,
                    "status": "incomplete",
                    "created_at": datetime.now(timezone.utc),
                    "updated_at": datetime.now(timezone.utc),
                    "data": {},  # CRS structure
                }
                
                # Add extracted fields (legacy structure)
                if fields.get("dob"):
                    try:
                        d = datetime.fromisoformat(fields["dob"]).date()
                        profile_data["dob"] = datetime.combine(d, datetime.min.time(), tzinfo=timezone.utc)
                        profile_data["data"]["dob"] = fields["dob"]
                    except Exception:
                        pass
                
                if fields.get("citizenship"):
                    profile_data["citizenship"] = fields["citizenship"]
                    profile_data["data"]["citizenship"] = fields["citizenship"]
                
                if fields.get("province"):
                    profile_data["province"] = fields["province"]
                
                if fields.get("city"):
                    profile_data["city"] = fields["city"]
                
                if fields.get("arrival_date"):
                    try:
                        d = datetime.fromisoformat(fields["arrival_date"]).date()
                        profile_data["arrival_date"] = datetime.combine(d, datetime.min.time(), tzinfo=timezone.utc)
                    except Exception:
                        pass
                
                # CRS fields -> profile.data
                if fields.get("marital_status"):
                    profile_data["data"]["marital_status"] = fields["marital_status"]
                
                if fields.get("spouse_accompanying") is not None:
                    profile_data["data"]["spouse_accompanying"] = fields["spouse_accompanying"]
                
                if fields.get("spouse_canadian_pr") is not None:
                    profile_data["data"]["spouse_canadian_pr"] = fields["spouse_canadian_pr"]
                
                # Education fields - store in both data (for CRS calculator) and education_json (for schema)
                education_data = {}
                if fields.get("education_level"):
                    profile_data["data"]["education_level"] = fields["education_level"]
                    education_data["education_level"] = fields["education_level"]
                
                if fields.get("education_level_detail"):
                    profile_data["data"]["education_level_detail"] = fields["education_level_detail"]
                    education_data["education_level_detail"] = fields["education_level_detail"]
                
                if fields.get("canadian_education") is not None:
                    profile_data["data"]["canadian_education"] = fields["canadian_education"]
                    education_data["canadian_education"] = fields["canadian_education"]
                
                # Store education in education_json at top level (as schema expects)
                if education_data:
                    profile_data["education_json"] = education_data
                
                # Language scores
                if fields.get("language_test_type") or any(fields.get(f"language_{skill}") is not None for skill in ["speaking", "listening", "reading", "writing"]):
                    lang_scores = {}
                    if fields.get("language_test_type"):
                        lang_scores["test"] = fields["language_test_type"]
                    for skill in ["speaking", "listening", "reading", "writing"]:
                        val = fields.get(f"language_{skill}")
                        if val is not None:
                            lang_scores[skill] = val
                    if lang_scores:
                        profile_data["data"]["language_scores"] = lang_scores
                
                # Second language
                if fields.get("second_language_test_type") or any(fields.get(f"second_language_{skill}") is not None for skill in ["speaking", "listening", "reading", "writing"]):
                    s2lang = {}
                    if fields.get("second_language_test_type"):
                        s2lang["test"] = fields["second_language_test_type"]
                    for skill in ["speaking", "listening", "reading", "writing"]:
                        val = fields.get(f"second_language_{skill}")
                        if val is not None:
                            s2lang[skill] = val
                    if s2lang:
                        profile_data["data"]["second_language_scores"] = s2lang
                        profile_data["data"]["has_second_language"] = True
                
                if fields.get("canadian_work_years") is not None:
                    profile_data["data"]["canadian_work_years"] = int(fields["canadian_work_years"])
                
                if fields.get("foreign_work_years") is not None:
                    profile_data["data"]["foreign_work_years"] = int(fields["foreign_work_years"])
                
                if fields.get("certificate_of_qualification") is not None:
                    profile_data["data"]["certificate_of_qualification"] = fields["certificate_of_qualification"]
                
                if fields.get("provincial_nomination") is not None:
                    profile_data["data"]["provincial_nomination"] = fields["provincial_nomination"]
                
                if fields.get("sibling_in_canada") is not None:
                    profile_data["data"]["sibling_in_canada"] = fields["sibling_in_canada"]
                
                # Spouse fields
                if fields.get("spouse_education_level"):
                    profile_data["data"]["spouse_education_level"] = fields["spouse_education_level"]
                
                if fields.get("spouse_canadian_work_years") is not None:
                    profile_data["data"]["spouse_canadian_work_years"] = int(fields["spouse_canadian_work_years"])
                
                if fields.get("spouse_language_test_type") or any(fields.get(f"spouse_language_{skill}") is not None for skill in ["speaking", "listening", "reading", "writing"]):
                    spouse_lang = {}
                    if fields.get("spouse_language_test_type"):
                        spouse_lang["test"] = fields["spouse_language_test_type"]
                    for skill in ["speaking", "listening", "reading", "writing"]:
                        val = fields.get(f"spouse_language_{skill}")
                        if val is not None:
                            spouse_lang[skill] = val
                    if spouse_lang:
                        profile_data["data"]["spouse_language_scores"] = spouse_lang
                
                # Legacy JSON fields
                if fields.get("education"):
                    profile_data["education_json"] = fields["education"]
                
                if fields.get("language_tests"):
                    profile_data["language_json"] = fields["language_tests"]
                
                if fields.get("work_experience"):
                    profile_data["work_json"] = fields["work_experience"]
                
                await db.profiles.insert_one(profile_data)
                logger.info(f"Created new profile for user {user_id}")
        else:
            logger.warning(f"Extraction status was not 'completed' or 'partial': {extraction_result.get('status')}")
            # Still try to detect document type even if extraction failed
            document_type = extraction_result.get("document_type", "unknown")
            if document_type != "unknown":
                await db.documents.update_one(
                    {"_id": ObjectId(document_id)},
                    {"$set": {"type_detected": document_type}}
                )
                logger.info(f"Updated document type to {document_type} despite extraction status")
        
    except Exception as e:
        # Log error but don't fail the upload
        logger.error(f"Error processing document {document_id}: {str(e)}", exc_info=True)
        # Try to update document with error status
        try:
            await db.documents.update_one(
                {"_id": ObjectId(document_id)},
                {"$set": {"type_detected": "unknown", "processing_error": str(e)}}
            )
        except:
            pass

@router.post("/documents", response_model=DocumentOut)
async def upload_document(
    request: Request,
    background: BackgroundTasks,
    file: UploadFile = File(...),
    user: dict = Depends(get_current_user)
):
    """Upload an immigration document"""
    if file.content_type not in ["application/pdf", "image/png", "image/jpeg", "image/jpg"]:
        raise HTTPException(status_code=400, detail="Upload PDF or PNG/JPEG image")

    user_id = ObjectId(user["id"])
    db = get_db(request)
    
    # Save file
    safe_name = os.path.basename(file.filename).replace(" ", "_")
    filename = f"{int(datetime.now().timestamp())}_{safe_name}"
    file_path = os.path.join(UPLOAD_DIR, filename)

    with open(file_path, "wb") as f:
        f.write(await file.read())

    # Create document record
    now = datetime.now(timezone.utc)
    document_data = {
        "user_id": user_id,
        "filename": file.filename,
        "mime_type": file.content_type,
        "storage_url": file_path,
        "type_detected": None,  # Will be set after extraction
        "created_at": now,
    }

    result = await db.documents.insert_one(document_data)
    document = await db.documents.find_one({"_id": result.inserted_id})

    # Process extraction in background
    background.add_task(process_document_extraction, request.app, str(result.inserted_id))

    return document_entity(document)

@router.get("/documents", response_model=List[DocumentOut])
async def list_documents(
    request: Request,
    user: dict = Depends(get_current_user)
):
    """Get list of all uploaded documents for the current user (includes passport from signup)"""
    db = get_db(request)
    user_id = ObjectId(user["id"])
    
    documents = []
    async for doc in db.documents.find({"user_id": user_id}).sort("created_at", -1):
        documents.append(document_entity(doc))
    
    # Also check signup_jobs for passport (backward compatibility for users who signed up before document records were created)
    signup_job = await db.signup_jobs.find_one({"user_id": user_id, "status": "completed"})
    if signup_job and signup_job.get("file_path"):
        # Check if passport already exists in documents
        passport_exists = any(
            doc.get("type_detected", "").lower() == "passport" 
            for doc in documents
        )
        
        if not passport_exists:
            # Add passport from signup
            file_path = signup_job["file_path"]
            mime_type = "application/pdf"
            if file_path.lower().endswith((".png", ".jpg", ".jpeg")):
                ext = file_path.split('.')[-1].lower()
                mime_type = f"image/{ext}"
            
            virtual_passport_doc = {
                "_id": signup_job["_id"],
                "user_id": user_id,
                "filename": os.path.basename(file_path),
                "mime_type": mime_type,
                "storage_url": file_path,
                "type_detected": "passport",
                "created_at": signup_job.get("created_at", datetime.now(timezone.utc)),
            }
            documents.insert(0, document_entity(virtual_passport_doc))
    
    return documents

@router.get("/documents/recommended", response_model=List[RecommendedDocument])
async def get_recommended_documents_list(
    request: Request,
    user: dict = Depends(get_current_user)
):
    """Get list of recommended documents based on permit type and uploaded documents"""
    db = get_db(request)
    user_id = ObjectId(user["id"])
    
    # Get uploaded documents to determine what's already uploaded
    uploaded_docs = []
    async for doc in db.documents.find({"user_id": user_id}):
        if doc.get("type_detected"):
            uploaded_docs.append(doc.get("type_detected"))
    
    # Detect permit type from uploaded documents
    permit_type = detect_permit_type_from_documents(uploaded_docs)
    
    # Also check profile for permit type hints
    profile = await db.profiles.find_one({"user_id": user_id})
    # Could add logic here to infer from profile data if needed
    
    # Get recommendations
    recommendations = get_recommended_documents(
        permit_type=permit_type,
        uploaded_document_types=uploaded_docs
    )
    
    return recommendations

@router.get("/documents/crs-status")
async def get_crs_documents_status(
    request: Request,
    user: dict = Depends(get_current_user)
):
    """
    Get comprehensive status of documents and CRS calculation readiness.
    
    Returns:
    - uploaded_documents: List of uploaded documents
    - required_documents: Documents needed for CRS calculation (includes passport if not uploaded)
    - crs_requirements: Analysis of CRS field requirements
    - can_calculate_crs: Always true - CRS can be calculated with partial data
    - is_complete: True if all required fields are present for complete calculation
    """
    db = get_db(request)
    user_id = ObjectId(user["id"])
    
    # Get uploaded documents from documents collection
    uploaded_documents = []
    uploaded_doc_types = []
    async for doc in db.documents.find({"user_id": user_id}).sort("created_at", -1):
        uploaded_documents.append(document_entity(doc))
        if doc.get("type_detected"):
            uploaded_doc_types.append(doc.get("type_detected"))
    
    # Also check signup_jobs for passport (in case it wasn't migrated to documents collection)
    # This handles cases where signup was completed before we started creating document records
    signup_job = await db.signup_jobs.find_one({"user_id": user_id, "status": "completed"})
    if signup_job and signup_job.get("file_path"):
        # Check if passport document already exists in documents collection
        passport_exists = any(
            doc.get("type_detected", "").lower() == "passport" 
            for doc in uploaded_documents
        )
        
        if not passport_exists:
            # Add passport from signup as a virtual document entry
            file_path = signup_job["file_path"]
            mime_type = "application/pdf"
            if file_path.lower().endswith((".png", ".jpg", ".jpeg")):
                ext = file_path.split('.')[-1].lower()
                mime_type = f"image/{ext}"
            
            # Create a virtual document dict that matches MongoDB document structure
            virtual_passport_doc = {
                "_id": signup_job["_id"],  # Use signup_job ID as document ID
                "user_id": user_id,
                "filename": os.path.basename(file_path),
                "mime_type": mime_type,
                "storage_url": file_path,
                "type_detected": "passport",
                "created_at": signup_job.get("created_at", datetime.now(timezone.utc)),
            }
            uploaded_documents.insert(0, document_entity(virtual_passport_doc))  # Add at beginning
            uploaded_doc_types.append("passport")
    
    # Get profile data
    profile = await db.profiles.find_one({"user_id": user_id})
    profile_data = {}
    if profile:
        profile_data = profile.get("data", {}) or {}
        # Also check root profile fields (for backward compatibility)
        if profile.get("dob") and not profile_data.get("dob"):
            dob_val = profile.get("dob")
            # Convert to ISO string format
            if isinstance(dob_val, datetime):
                profile_data["dob"] = dob_val.date().isoformat()
            elif isinstance(dob_val, date):
                profile_data["dob"] = dob_val.isoformat()
            else:
                profile_data["dob"] = str(dob_val)
        
        # Marital status - default to "single" if null/empty
        if not profile_data.get("marital_status") and profile.get("marital_status"):
            profile_data["marital_status"] = profile.get("marital_status")
        elif not profile_data.get("marital_status"):
            # Default to single if not provided (passport doesn't show marriage = unmarried)
            profile_data["marital_status"] = "single"
        
        # Calculate age from DOB if age is not provided
        if not profile_data.get("age") and profile_data.get("dob"):
            try:
                dob_str = profile_data["dob"]
                if isinstance(dob_str, str):
                    # Try ISO format first
                    try:
                        dob_date = datetime.fromisoformat(dob_str.replace("Z", "+00:00")).date()
                    except:
                        # Try YYYY-MM-DD format
                        dob_date = datetime.strptime(dob_str, "%Y-%m-%d").date()
                elif isinstance(dob_str, datetime):
                    dob_date = dob_str.date()
                elif isinstance(dob_str, date):
                    dob_date = dob_str
                else:
                    dob_date = None
                
                if dob_date:
                    today = date.today()
                    age_calculated = today.year - dob_date.year - ((today.month, today.day) < (dob_date.month, dob_date.day))
                    if age_calculated > 0 and age_calculated < 120:
                        profile_data["age"] = age_calculated
            except Exception:
                pass
    
    # Analyze CRS requirements
    crs_analysis = analyze_crs_requirements(profile_data)
    
    # Get required documents for CRS
    required_docs = get_required_documents_for_crs(profile_data, uploaded_doc_types)
    
    return {
        "uploaded_documents": uploaded_documents,
        "uploaded_count": len(uploaded_documents),
        "required_documents": required_docs,
        "required_count": len(required_docs),
        "crs_requirements": {
            "can_calculate": crs_analysis["can_calculate"],
            "is_complete": crs_analysis.get("is_complete", False),
            "available_fields": crs_analysis["available_fields"],
            "missing_required": crs_analysis["missing_required"],
            "missing_optional": crs_analysis["missing_optional"],
            "field_details": crs_analysis["requirements"],
        },
        "can_calculate_crs": crs_analysis["can_calculate"],  # Always true - calculator works with partial data
        "is_complete": crs_analysis.get("is_complete", False),  # True if all required fields present
        "completion_percentage": _calculate_completion_percentage(crs_analysis),
    }

def _calculate_completion_percentage(analysis: dict) -> int:
    """Calculate completion percentage for CRS calculation"""
    total_fields = len(analysis["requirements"])
    if total_fields == 0:
        return 0
    
    available_count = len(analysis["available_fields"])
    return int((available_count / total_fields) * 100)

@router.get("/documents/{document_id}", response_model=DocumentOut)
async def get_document(
    document_id: str,
    request: Request,
    user: dict = Depends(get_current_user)
):
    """Get a specific document by ID"""
    db = get_db(request)
    user_id = ObjectId(user["id"])
    
    if not ObjectId.is_valid(document_id):
        raise HTTPException(status_code=400, detail="Invalid document ID")
    
    document = await db.documents.find_one({"_id": ObjectId(document_id), "user_id": user_id})
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    return document_entity(document)

@router.delete("/documents/{document_id}")
async def delete_document(
    document_id: str,
    request: Request,
    user: dict = Depends(get_current_user)
):
    """Delete a document"""
    db = get_db(request)
    user_id = ObjectId(user["id"])
    
    if not ObjectId.is_valid(document_id):
        raise HTTPException(status_code=400, detail="Invalid document ID")
    
    document = await db.documents.find_one({"_id": ObjectId(document_id), "user_id": user_id})
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Delete file if it exists
    file_path = document.get("storage_url")
    if file_path and os.path.exists(file_path):
        try:
            os.remove(file_path)
        except Exception as e:
            print(f"Error deleting file {file_path}: {str(e)}")
    
    result = await db.documents.delete_one({"_id": ObjectId(document_id), "user_id": user_id})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Document not found")
    
    return {"message": "Document deleted successfully"}
