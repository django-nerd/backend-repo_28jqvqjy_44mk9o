import os
import threading
import time
from typing import List, Optional, Literal

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from bson import ObjectId

from database import db, create_document, get_documents

app = FastAPI(title="Multi AI Video Generator API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------- Utilities ---------

def to_str_id(doc: dict) -> dict:
    if not doc:
        return doc
    d = dict(doc)
    if "_id" in d:
        d["id"] = str(d.pop("_id"))
    # Cast datetime to isoformat if present
    for k, v in list(d.items()):
        if hasattr(v, "isoformat"):
            d[k] = v.isoformat()
    return d

PROVIDERS = [
    {"key": "gemini", "name": "Gemini AI"},
    {"key": "wan2_1", "name": "WAN 2.1"},
    {"key": "grok", "name": "Grok AI"},
    {"key": "hailuo", "name": "Hailuo AI"},
    {"key": "sora2", "name": "Sora 2"},
]

# -------- Models ---------

class CreateJobRequest(BaseModel):
    provider: Literal["gemini", "wan2_1", "grok", "hailuo", "sora2"]
    prompt: str = Field(..., min_length=3, max_length=2000)
    aspect_ratio: Literal["16:9", "9:16", "1:1", "4:3"] = "16:9"
    duration: int = Field(5, ge=1, le=60)

class JobResponse(BaseModel):
    id: str
    provider: str
    prompt: str
    aspect_ratio: str
    duration: int
    status: Literal["queued", "processing", "completed", "failed"]
    result_url: Optional[str] = None
    error: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

# -------- Background simulation ---------

def simulate_job(job_id: str, provider: str, duration: int):
    try:
        # Mark processing
        db["videojob"].update_one({"_id": ObjectId(job_id)}, {"$set": {"status": "processing"}})
        # Simulate processing time based on duration (but capped)
        wait_time = min(max(duration // 2, 2), 8)
        time.sleep(wait_time)
        # Produce a demo video URL (reliable CORS-friendly public sample)
        demo_url = "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4"
        db["videojob"].update_one(
            {"_id": ObjectId(job_id)},
            {"$set": {"status": "completed", "result_url": demo_url}}
        )
    except Exception as e:
        db["videojob"].update_one(
            {"_id": ObjectId(job_id)},
            {"$set": {"status": "failed", "error": str(e)[:200]}}
        )

# -------- Routes ---------

@app.get("/")
def read_root():
    return {"message": "Multi AI Video Generator API running"}

@app.get("/api/providers")
def list_providers():
    return {"providers": PROVIDERS}

@app.post("/api/jobs", response_model=JobResponse)
def create_job(payload: CreateJobRequest):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    data = payload.model_dump()
    data.update({"status": "queued", "result_url": None, "error": None})
    job_id = create_document("videojob", data)

    # Start background simulation thread
    t = threading.Thread(target=simulate_job, args=(job_id, payload.provider, payload.duration), daemon=True)
    t.start()

    doc = db["videojob"].find_one({"_id": ObjectId(job_id)})
    return JobResponse(**to_str_id(doc))

@app.get("/api/jobs", response_model=List[JobResponse])
def list_jobs(limit: int = 20):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    docs = db["videojob"].find({}).sort("created_at", -1).limit(limit)
    return [JobResponse(**to_str_id(d)) for d in docs]

@app.get("/api/jobs/{job_id}", response_model=JobResponse)
def get_job(job_id: str):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    try:
        doc = db["videojob"].find_one({"_id": ObjectId(job_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid job id")
    if not doc:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobResponse(**to_str_id(doc))

@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }
    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Configured"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"
    import os as _os
    response["database_url"] = "✅ Set" if _os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if _os.getenv("DATABASE_NAME") else "❌ Not Set"
    return response

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
