import os
from datetime import datetime
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from starlette.middleware.sessions import SessionMiddleware
from bson import ObjectId

from database import db, create_document, get_documents

app = FastAPI(title="Portfolio API")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Sessions for simple admin auth
SESSION_SECRET = os.getenv("SESSION_SECRET", "change-me-secret")
app.add_middleware(SessionMiddleware, secret_key=SESSION_SECRET)

# --------- Models (lightweight for requests) ---------
class SkillIn(BaseModel):
    title: str
    slug: str
    icon: Optional[str] = None
    summary: Optional[str] = None
    link: Optional[str] = None
    tags: List[str] = []
    order: int = 0

class ExperienceIn(BaseModel):
    company: str
    role: str
    startDate: str  # ISO date
    endDate: Optional[str] = None
    summary: Optional[str] = None
    image: Optional[str] = None
    order: int = 0

class BlogPostIn(BaseModel):
    title: str
    slug: str
    excerpt: Optional[str] = None
    content: str = ""
    coverImage: Optional[str] = None
    tags: List[str] = []
    published: bool = True

# --------- Utilities ---------
COLLECTIONS = {
    'skills': 'skill',
    'experiences': 'experience',
    'blogs': 'blogpost'
}

def admin_required(request: Request):
    if not request.session.get("admin"):
        raise HTTPException(status_code=401, detail="Unauthorized")
    return True

# --------- Health / Test ---------
@app.get("/")
def root():
    return {"message": "Portfolio API running"}

@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set",
        "database_name": "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set",
        "connection_status": "Not Connected",
        "collections": []
    }
    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["connection_status"] = "Connected"
            try:
                response["collections"] = db.list_collection_names()
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️ Connected but error: {str(e)[:80]}"
        else:
            response["database"] = "⚠️ Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:80]}"
    return response

# --------- Auth ---------
@app.post("/api/admin/login")
async def admin_login(payload: dict, request: Request):
    password = str(payload.get("password", ""))
    expected = os.getenv("ADMIN_PASSWORD", "admin")
    if password == expected:
        request.session["admin"] = True
        return {"ok": True}
    raise HTTPException(status_code=401, detail="Invalid credentials")

@app.post("/api/admin/logout")
async def admin_logout(request: Request):
    request.session.clear()
    return {"ok": True}

@app.get("/api/admin/session")
async def admin_session(request: Request):
    return {"admin": bool(request.session.get("admin"))}

# --------- Public GET endpoints ---------
@app.get("/api/skills")
def get_skills(limit: int = 100):
    docs = db[COLLECTIONS['skills']].find({}).sort("order", 1).limit(limit)
    return [{"id": str(d.get("_id")), **{k: v for k, v in d.items() if k != "_id"}} for d in docs]

@app.get("/api/skills/{slug}")
def get_skill(slug: str):
    d = db[COLLECTIONS['skills']].find_one({"slug": slug})
    if not d:
        raise HTTPException(404, "Not found")
    return {"id": str(d.get("_id")), **{k: v for k, v in d.items() if k != "_id"}}

@app.get("/api/experiences")
def get_experiences(limit: int = 100):
    docs = db[COLLECTIONS['experiences']].find({}).sort("order", 1).limit(limit)
    return [{"id": str(d.get("_id")), **{k: v for k, v in d.items() if k != "_id"}} for d in docs]

@app.get("/api/blogs")
def get_blogs(limit: int = 100):
    docs = db[COLLECTIONS['blogs']].find({"published": True}).sort("created_at", -1).limit(limit)
    return [{"id": str(d.get("_id")), **{k: v for k, v in d.items() if k != "_id"}} for d in docs]

@app.get("/api/blogs/{slug}")
def get_blog(slug: str):
    d = db[COLLECTIONS['blogs']].find_one({"slug": slug, "published": True})
    if not d:
        raise HTTPException(404, "Not found")
    return {"id": str(d.get("_id")), **{k: v for k, v in d.items() if k != "_id"}}

# --------- Admin CRUD ---------
@app.post("/api/admin/skills", dependencies=[Depends(admin_required)])
def create_skill(skill: SkillIn):
    _id = create_document(COLLECTIONS['skills'], skill.model_dump())
    return {"id": _id}

@app.put("/api/admin/skills/{doc_id}", dependencies=[Depends(admin_required)])
def update_skill(doc_id: str, skill: SkillIn):
    if not ObjectId.is_valid(doc_id):
        raise HTTPException(400, "Invalid id")
    res = db[COLLECTIONS['skills']].update_one(
        {"_id": ObjectId(doc_id)},
        {"$set": {**skill.model_dump(), "updated_at": datetime.utcnow()}}
    )
    if res.matched_count == 0:
        raise HTTPException(404, "Not found")
    return {"ok": True}

@app.delete("/api/admin/skills/{doc_id}", dependencies=[Depends(admin_required)])
def delete_skill(doc_id: str):
    if not ObjectId.is_valid(doc_id):
        raise HTTPException(400, "Invalid id")
    res = db[COLLECTIONS['skills']].delete_one({"_id": ObjectId(doc_id)})
    return {"deleted": res.deleted_count}

@app.post("/api/admin/experiences", dependencies=[Depends(admin_required)])
def create_experience(exp: ExperienceIn):
    data = exp.model_dump()
    _id = create_document(COLLECTIONS['experiences'], data)
    return {"id": _id}

@app.put("/api/admin/experiences/{doc_id}", dependencies=[Depends(admin_required)])
def update_experience(doc_id: str, exp: ExperienceIn):
    if not ObjectId.is_valid(doc_id):
        raise HTTPException(400, "Invalid id")
    res = db[COLLECTIONS['experiences']].update_one(
        {"_id": ObjectId(doc_id)},
        {"$set": {**exp.model_dump(), "updated_at": datetime.utcnow()}}
    )
    if res.matched_count == 0:
        raise HTTPException(404, "Not found")
    return {"ok": True}

@app.delete("/api/admin/experiences/{doc_id}", dependencies=[Depends(admin_required)])
def delete_experience(doc_id: str):
    if not ObjectId.is_valid(doc_id):
        raise HTTPException(400, "Invalid id")
    res = db[COLLECTIONS['experiences']].delete_one({"_id": ObjectId(doc_id)})
    return {"deleted": res.deleted_count}

@app.post("/api/admin/blogs", dependencies=[Depends(admin_required)])
def create_blog(post: BlogPostIn):
    _id = create_document(COLLECTIONS['blogs'], post.model_dump())
    return {"id": _id}

@app.put("/api/admin/blogs/{doc_id}", dependencies=[Depends(admin_required)])
def update_blog(doc_id: str, post: BlogPostIn):
    if not ObjectId.is_valid(doc_id):
        raise HTTPException(400, "Invalid id")
    res = db[COLLECTIONS['blogs']].update_one(
        {"_id": ObjectId(doc_id)},
        {"$set": {**post.model_dump(), "updated_at": datetime.utcnow()}}
    )
    if res.matched_count == 0:
        raise HTTPException(404, "Not found")
    return {"ok": True}

@app.delete("/api/admin/blogs/{doc_id}", dependencies=[Depends(admin_required)])
def delete_blog(doc_id: str):
    if not ObjectId.is_valid(doc_id):
        raise HTTPException(400, "Invalid id")
    res = db[COLLECTIONS['blogs']].delete_one({"_id": ObjectId(doc_id)})
    return {"deleted": res.deleted_count}


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
