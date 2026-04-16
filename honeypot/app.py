from flask import Flask, request
import time, os, yaml, json
from deception import deception_router

app = Flask(__name__)

# Load config
with open("config.yaml") as f:
    CONFIG = yaml.safe_load(f)

REQUEST_LOG = CONFIG["logging"]["request_log"]
DECEPTION_LOG = CONFIG["logging"]["deception_log"]

os.makedirs("logs", exist_ok=True)
os.makedirs("sessions", exist_ok=True)

# In-memory session → persona map (simple for now)
SESSION_PERSONA = {}

def get_session_id():
    return f"{request.remote_addr}_{request.headers.get('User-Agent')}"

def detect_persona(user_agent):
    ua = user_agent.lower()
    if "sqlmap" in ua or "nikto" in ua or "nmap" in ua:
        return "automated_scanner"
    elif "curl" in ua:
        return "script_kiddie"
    return "unknown"

def get_persona(session_id):
    if session_id not in SESSION_PERSONA:
        ua = request.headers.get("User-Agent", "")
        SESSION_PERSONA[session_id] = detect_persona(ua)
    return SESSION_PERSONA[session_id]

def log_request(session_id):
    with open(REQUEST_LOG, "a") as f:
        f.write(
            f"{time.time()} | {session_id} | "
            f"{request.method} | {request.full_path}\n"
        )

def log_deception(session_id, persona, action):
    with open(DECEPTION_LOG, "a") as f:
        f.write(
            f"{time.time()} | {session_id} | {persona} | {action}\n"
        )

@app.before_request
def before_request():
    session_id = get_session_id()
    log_request(session_id)

@app.route("/")
def index():
    return "Welcome to Company Portal"

@app.route("/login", methods=["GET", "POST"])
def login():
    session_id = get_session_id()
    persona = get_persona(session_id)
    resp, code = deception_router(persona, request)
    log_deception(session_id, persona, "login")
    return resp, code

@app.route("/search")
def search():
    session_id = get_session_id()
    persona = get_persona(session_id)
    resp, code = deception_router(persona, request)
    log_deception(session_id, persona, "search")
    return resp, code

@app.route("/download")
def download():
    session_id = get_session_id()
    persona = get_persona(session_id)
    resp, code = deception_router(persona, request)
    log_deception(session_id, persona, "download")
    return resp, code

@app.route("/upload", methods=["POST"])
def upload():
    session_id = get_session_id()
    persona = get_persona(session_id)
    resp, code = deception_router(persona, request)
    log_deception(session_id, persona, "upload")
    return resp, code

# 🔹 Endpoint for QNN / pipeline to update persona
@app.route("/update_persona", methods=["POST"])
def update_persona():
    data = request.json
    SESSION_PERSONA[data["session_id"]] = data["persona"]
    return {"status": "updated"}, 200

if __name__ == "__main__":
    app.run(
        host=CONFIG["honeypot"]["host"],
        port=CONFIG["honeypot"]["port"]
    )
