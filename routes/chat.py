"""
Chat API: fixed prompts (GET) and chat with immigration consultant (POST).

The agent uses the user's profile, uploaded documents, and CRS score.
It uses web search to fetch current CRS cutoffs, draw dates, and news.
Not legal advice.
"""

from __future__ import annotations

import asyncio
import json
from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from bson import ObjectId

from app.auth.deps import get_current_user
from app.db import get_db
from app.ai.chat_prompts import get_fixed_prompts
from app.ai.chat_agent import run_immigration_chat
from app.ai.crs_agent import profile_to_crs_input
from app.ai.crs_dynamic import compute_crs
from models.chat import ChatRequest, ChatResponse

router = APIRouter(tags=["chat"])


def _build_profile_data(doc: dict | None) -> dict:
    """Build profile data dict from DB profile (same shape as eligibility CRS)."""
    data = dict((doc or {}).get("data", {}))
    if not doc:
        return data

    if not data.get("dob") and doc.get("dob"):
        dob_val = doc["dob"]
        if isinstance(dob_val, datetime):
            data["dob"] = dob_val.date().isoformat()
        elif isinstance(dob_val, date):
            data["dob"] = dob_val.isoformat()
        else:
            data["dob"] = str(dob_val)

    if not data.get("marital_status") and doc.get("marital_status"):
        data["marital_status"] = doc["marital_status"]
    elif not data.get("marital_status"):
        data["marital_status"] = "single"

    if doc.get("education_json") and isinstance(doc["education_json"], dict):
        ej = doc["education_json"]
        if not data.get("education_level") and ej.get("education_level"):
            data["education_level"] = ej["education_level"]
        if not data.get("education_level_detail") and ej.get("education_level_detail"):
            data["education_level_detail"] = ej["education_level_detail"]
        if data.get("canadian_education") is None and ej.get("canadian_education") is not None:
            data["canadian_education"] = ej["canadian_education"]

    if not data.get("age") and data.get("dob"):
        try:
            dob_str = data["dob"]
            dob_date = None
            if isinstance(dob_str, str):
                try:
                    dob_date = datetime.fromisoformat(dob_str.replace("Z", "+00:00")).date()
                except Exception:
                    try:
                        dob_date = datetime.strptime(dob_str, "%Y-%m-%d").date()
                    except Exception:
                        for fmt in ["%d/%m/%Y", "%m/%d/%Y", "%Y/%m/%d", "%d-%m-%Y", "%m-%d-%Y"]:
                            try:
                                dob_date = datetime.strptime(dob_str, fmt).date()
                                break
                            except Exception:
                                continue
            elif isinstance(dob_str, datetime):
                dob_date = dob_str.date()
            elif isinstance(dob_str, date):
                dob_date = dob_str
            if dob_date:
                today = date.today()
                age_calc = today.year - dob_date.year - (
                    (today.month, today.day) < (dob_date.month, dob_date.day)
                )
                if 0 < age_calc < 120:
                    data["age"] = age_calc
        except Exception:
            pass

    for key in ("province", "city", "citizenship", "arrival_date", "date_of_expiry", "date_of_issue"):
        if not data.get(key) and doc.get(key) is not None:
            v = doc[key]
            if isinstance(v, (datetime, date)):
                data[key] = v.date().isoformat() if hasattr(v, "date") else v.isoformat()
            else:
                data[key] = v

    return data


async def _documents_for_context(db, user_id: ObjectId) -> list[dict]:
    """Fetch documents list (including virtual passport) for chat context."""
    docs = []
    async for d in db.documents.find({"user_id": user_id}).sort("created_at", -1):
        docs.append({
            "filename": d.get("filename"),
            "type_detected": d.get("type_detected"),
            "storage_url": d.get("storage_url"),
        })
    signup = await db.signup_jobs.find_one({"user_id": user_id, "status": "completed"})
    if signup and signup.get("file_path"):
        if not any((x.get("type_detected") or "").lower() == "passport" for x in docs):
            docs.insert(0, {
                "filename": signup["file_path"].split("/")[-1],
                "type_detected": "passport",
                "storage_url": signup["file_path"],
            })
    return docs


@router.get("/chat/prompts")
async def get_chat_prompts():
    """
    Return the fixed prompt set for the immigration chat UI.

    Categories: CRS Score, Eligibility, Timeline, PNP Questions,
    Status/Expiry/Deadlines. Use these as quick-pick suggestions.
    """
    return {"categories": get_fixed_prompts()}


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: Request,
    body: ChatRequest,
    user: dict = Depends(get_current_user),
):
    """
    Chat with the immigration consultant AI agent.

    The agent sees the user's profile, uploaded documents (in system uploads folder),
    and CRS score (when computable). It uses web search to fetch current CRS cutoffs,
    draw dates, and immigration news. It answers questions about CRS, eligibility,
    timelines, PNP, status/expiry, and pathways.

    Optional `history` enables multi-turn conversation.
    """
    db = get_db(request)
    user_id = ObjectId(user["id"])

    profile_doc = await db.profiles.find_one({"user_id": user_id})
    data = _build_profile_data(profile_doc)
    documents = await _documents_for_context(db, user_id)

    crs_result = None
    try:
        inp = profile_to_crs_input(data)
        res = compute_crs(inp)
        crs_result = {
            "total": res.total,
            "breakdown": res.breakdown,
            "missing_or_defaulted": res.missing_or_defaulted,
            "disclaimer": res.disclaimer,
        }
    except Exception:
        pass

    profile_context = json.dumps(data, indent=2, default=str)
    documents_context = "\n".join(
        f"- {(d.get('filename') or d.get('storage_url') or 'unknown')} (type: {d.get('type_detected') or 'unknown'})"
        for d in documents
    ) or "No documents uploaded yet."
    if crs_result:
        crs_context = (
            f"Total CRS: {crs_result['total']}\n"
            f"Breakdown: {json.dumps(crs_result['breakdown'], default=str)}\n"
            + (f"Missing/defaulted: {', '.join(crs_result['missing_or_defaulted'])}\n" if crs_result.get("missing_or_defaulted") else "")
            + (f"Note: {crs_result['disclaimer']}" if crs_result.get("disclaimer") else "")
        )
    else:
        crs_context = "CRS score has not been computed."

    history = None
    if body.history:
        history = [{"role": m.role, "content": m.content} for m in body.history]

    loop = asyncio.get_running_loop()
    try:
        reply = await loop.run_in_executor(
            None,
            lambda: run_immigration_chat(
                profile_context=profile_context,
                documents_context=documents_context,
                crs_context=crs_context,
                user_message=body.message,
                history=history,
            ),
        )
    except RuntimeError as e:
        if "OPENROUTER_API_KEY" in str(e):
            raise HTTPException(
                status_code=503,
                detail="Chat service unavailable. OPENROUTER_API_KEY is not configured.",
            )
        raise HTTPException(status_code=500, detail=str(e))

    return ChatResponse(reply=reply)
