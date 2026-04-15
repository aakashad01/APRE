from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
import httpx
import random
from typing import Optional
from .logger import QAPRELogger
from .deception import DeceptionEngine
import time

app = FastAPI(title="Q-APRE Vulnerable Honeypot")

# Initialize Deception Engine
deception_engine = DeceptionEngine()

# Add our custom logger middleware
app.add_middleware(QAPRELogger)

@app.middleware("http")
async def deception_middleware(request: Request, call_next):
    # 1. IDENTIFY: In prod, this calls the QNN. Here we use the tag for demo.
    persona = request.headers.get("X-Persona-Tag", "benign")
    
    # 2. DECIDE: Get strategy
    strategy = deception_engine.get_response_strategy(persona)
    
    # 3. ACT: Apply Delay (Tarpit)
    if strategy["delay"] > 0:
        time.sleep(strategy["delay"])
        
    response = await call_next(request)
    
    # 4. ACT: Inject Content (e.g. Fake Admin comments)
    # (Simplified for demo)
    return response

# --- FAKE DATABASE ---
USERS = {
    "1001": {"name": "Alice Admin", "role": "admin", "secret": "s3cr3t_k3y_x99"},
    "1002": {"name": "Bob User", "role": "user", "secret": "bob_notes.txt"},
    "1003": {"name": "Charlie Guest", "role": "guest", "secret": "guest_wifi_pass"},
}

@app.get("/")
def home():
    return {"message": "Welcome to the internal employee portal. Please login."}

# --- VULNERABILITY 1: IDOR (Insecure Direct Object Reference) ---
# Goal: Attacker detects they can change 'user_id' to see others' data.
@app.get("/user/{user_id}")
def get_user_profile(user_id: str):
    # VULNERABILITY: No check if the requester is actually user_id.
    user = USERS.get(user_id)
    if user:
        return {"status": "success", "data": user}
    else:
        # Returning 404 is correct, but the *pattern* of scanning is what we catch.
        raise HTTPException(status_code=404, detail="User not found")

# --- VULNERABILITY 2: SSRF (Server-Side Request Forgery) ---
# Goal: Attacker makes the server fetch internal URLs (e.g., localhost:8000/admin, metadata)
@app.get("/fetch")
async def fetch_url(url: str):
    # VULNERABILITY: No allowlist/denylist.
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, timeout=2.0)
            return {"status": "success", "fetched_content": resp.text[:200]} # Return preview
    except Exception as e:
        return {"status": "error", "detail": str(e)}

# --- BAIT: FAKE ADMIN ---
@app.get("/admin")
def admin_panel():
    # Only accessible via localhost (or SSRF)
    return {"message": "ADMIN PANEL - RESTRICTED", "flag": "QAPRE{SSRF_SUCCESSFUL}"}

# --- LOGIN (Brute Force Target) ---
@app.post("/login")
def login(data: dict):
    username = data.get("username")
    password = data.get("password")
    
    # Simulate login check
    if username == "admin" and password == "admin123":
        return {"status": "success", "token": "admin_token_jwt"}
    
    # VULNERABILITY: Enum (Wait time or specific error message)
    # Here we just return failure.
    return JSONResponse(status_code=401, content={"status": "failed", "error": "Invalid credentials"})
