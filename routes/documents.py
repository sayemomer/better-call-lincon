import os
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, UploadFile, File, BackgroundTasks, Request, Depends
from bson import ObjectId
from typing import List
from app.db import get_db
from app.auth.deps import get_current_user
from app.ai.immigration_agent import run_immigration_extraction_crew
from app.utils.document_recommendations import get_recommended_documents, detect_permit_type_from_documents
from models.document import DocumentOut, RecommendedDocument, document_entity

router = APIRouter(tags=["documents"])

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

async def process_document_extraction(app, document_id: str):
    """Background task to extract profile data from uploaded document"""
    if not ObjectId.is_valid(document_id):
        return

    client = getattr(app.state, "mongo_client", None)
    if client is None:
        return

    db_name = getattr(app.state, "db_name", "fastapi_crud")
    db = client[db_name]

    document = await db.documents.find_one({"_id": ObjectId(document_id)})
    if not document:
        return

    try:
        file_path = document["storage_url"]
        
        # Extract data from document
        extraction_result = run_immigration_extraction_crew(file_path)
        
        if extraction_result.get("status") in ["completed", "partial"]:
            fields = extraction_result.get("fields", {})
            document_type = extraction_result.get("document_type", "unknown")
            
            # Update document with detected type
            await db.documents.update_one(
                {"_id": ObjectId(document_id)},
                {"$set": {"type_detected": document_type}}
            )
            
            # Update profile with extracted data
            user_id = document["user_id"]
            profile = await db.profiles.find_one({"user_id": user_id})
            
            if profile:
                update_data = {}
                profile_data_dict = profile.get("data", {})  # For backend CRS structure
                
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
                
                # Education CRS fields
                if fields.get("education_level"):
                    profile_data_dict["education_level"] = fields["education_level"]
                
                if fields.get("education_level_detail"):
                    profile_data_dict["education_level_detail"] = fields["education_level_detail"]
                
                if fields.get("canadian_education") is not None:
                    profile_data_dict["canadian_education"] = fields["canadian_education"]
                
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
                    existing_edu = profile.get("education_json") or {}
                    if isinstance(existing_edu, dict) and isinstance(fields["education"], dict):
                        existing_edu.update(fields["education"])
                        update_data["education_json"] = existing_edu
                    else:
                        update_data["education_json"] = fields["education"]
                
                if fields.get("language_tests"):
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
                
                # Update profile.data with CRS structure
                if profile_data_dict:
                    update_data["data"] = profile_data_dict
                
                if update_data:
                    update_data["updated_at"] = datetime.now(timezone.utc)
                    await db.profiles.update_one(
                        {"user_id": user_id},
                        {"$set": update_data}
                    )
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
                
                if fields.get("education_level"):
                    profile_data["data"]["education_level"] = fields["education_level"]
                
                if fields.get("education_level_detail"):
                    profile_data["data"]["education_level_detail"] = fields["education_level_detail"]
                
                if fields.get("canadian_education") is not None:
                    profile_data["data"]["canadian_education"] = fields["canadian_education"]
                
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
        
    except Exception as e:
        # Log error but don't fail the upload
        print(f"Error processing document {document_id}: {str(e)}")

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
    """Get list of all uploaded documents for the current user"""
    db = get_db(request)
    user_id = ObjectId(user["id"])
    
    documents = []
    async for doc in db.documents.find({"user_id": user_id}).sort("created_at", -1):
        documents.append(document_entity(doc))
    
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
