import time
import json
import uuid
import os
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from datetime import datetime

# Direct path to logs
LOG_DIR = os.path.join(os.getcwd(), "data", "raw_logs")
os.makedirs(LOG_DIR, exist_ok=True)

class QAPRELogger(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        request_id = str(uuid.uuid4())
        
        # Capture Request Body (careful: consuming stream)
        # We need to read and then put it back for the app
        body_bytes = await request.body()
        try:
            body_json = json.loads(body_bytes) if body_bytes else {}
        except:
            body_json = {"raw": body_bytes.decode('utf-8', errors='ignore')}

        # Re-inject body for the actual route handler
        async def receive():
            return {"type": "http.request", "body": body_bytes}
        request._receive = receive
        
        # Process the request
        response = await call_next(request)
        
        process_time = time.time() - start_time
        
        # Log Entry
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "request_id": request_id,
            "client_ip": request.client.host,
            "persona_tag": request.headers.get("X-Persona-Tag", "benign"), # Capture Label
            "method": request.method,
            "url": str(request.url),
            "path": request.url.path,
            "query_params": dict(request.query_params),
            "headers": dict(request.headers),
            "body": body_json,
            "status_code": response.status_code,
            "response_time": process_time
        }
        
        # Save to file (One file per request for simplicity in high-concurrency simulation)
        # In prod, we'd use a queue or database
        filename = f"session_{int(time.time())}_{request_id[:8]}.json"
        filepath = os.path.join(LOG_DIR, filename)
        
        with open(filepath, "w") as f:
            json.dump(log_entry, f, indent=4)
            
        return response
