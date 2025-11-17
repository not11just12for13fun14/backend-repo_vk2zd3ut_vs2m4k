import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from database import db, create_document, get_documents
from schemas import User, BlogPost, ContactMessage

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "SaaS Backend Running"}

# Pricing plans endpoint (static from backend for now)
class Plan(BaseModel):
    id: str
    name: str
    price: str
    features: List[str]
    highlighted: bool = False

@app.get("/api/plans", response_model=List[Plan])
def get_plans():
    return [
        Plan(id="free", name="Starter", price="$0", features=["Up to 3 projects", "Basic analytics", "Community support"], highlighted=False),
        Plan(id="pro", name="Pro", price="$19", features=["Unlimited projects", "Advanced analytics", "Priority support"], highlighted=True),
        Plan(id="team", name="Team", price="$49", features=["Team workspaces", "SSO (SAML)", "Admin controls"], highlighted=False),
    ]

# Simple auth endpoints (signup/login) - for demo; store users
class SignupPayload(BaseModel):
    name: str
    email: str
    password: str

class LoginPayload(BaseModel):
    email: str
    password: str

@app.post("/api/auth/signup")
def signup(payload: SignupPayload):
    # very basic hash replacement for demo, not real security
    from hashlib import sha256
    user = User(name=payload.name, email=payload.email, password_hash=sha256(payload.password.encode()).hexdigest())
    try:
        user_id = create_document("user", user)
        return {"ok": True, "id": user_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/auth/login")
def login(payload: LoginPayload):
    # naive demo: check if email exists; in real app validate password
    try:
        docs = get_documents("user", {"email": payload.email}, limit=1)
        if not docs:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        return {"ok": True, "message": "Logged in"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Blog endpoints
class BlogCreatePayload(BaseModel):
    title: str
    slug: str
    content: str
    excerpt: Optional[str] = None
    author: str
    tags: List[str] = []
    published: bool = True

@app.post("/api/blog")
def create_blog(payload: BlogCreatePayload):
    post = BlogPost(**payload.model_dump())
    try:
        post_id = create_document("blogpost", post)
        return {"ok": True, "id": post_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/blog")
def list_blogs(limit: int = 10):
    try:
        posts = get_documents("blogpost", {"published": True}, limit=limit)
        # convert ObjectId to str if present
        for p in posts:
            if "_id" in p:
                p["id"] = str(p.pop("_id"))
        return posts
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Contact form endpoint
class ContactPayload(BaseModel):
    name: str
    email: str
    message: str

@app.post("/api/contact")
def submit_contact(payload: ContactPayload):
    msg = ContactMessage(**payload.model_dump())
    try:
        msg_id = create_document("contactmessage", msg)
        return {"ok": True, "id": msg_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

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

    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"
    return response

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
