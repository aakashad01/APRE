import time, random

def fake_sql_error(payload):
    payload = payload.lower()

    # Boolean TRUE patterns
    if any(x in payload for x in ["1=1", "true", "or 1", "and 1"]):
        return "A" * (800 + random.randint(0, 50)), 200

    # Boolean FALSE patterns
    elif any(x in payload for x in ["1=2", "false", "and 0"]):
        return "B" * (50 + random.randint(0, 10)), 200

    # Time-based
    elif "sleep" in payload or "benchmark" in payload:
        time.sleep(5)
        return "Query executed", 200

    # Error-based patterns
    elif any(x in payload for x in ["extractvalue", "updatexml", "floor"]):
        return """
XPATH syntax error: '~mysql~'
MySQL server version: 5.7.31-log
Warning: mysql_fetch_array()
""", 500

    # Default fallback
    return "Request processed", 200

def fake_sensitive_file():
    return """DB_USER=admin
DB_PASS=admin123
APP_ENV=production
SECRET_KEY=devkey
""", 200

def fake_admin_login():
    return "Invalid password (1 attempt remaining)", 401

def slow_response():
    time.sleep(3)
    return "Processing request...", 200

def normal_response():
    return "Request processed", 200


def deception_router(persona, request):
    payload = request.args.get("q", "")

    if persona == "automated_scanner":
        return fake_sql_error(payload)

    elif persona == "script_kiddie":
        return fake_sql_error(payload)

    elif persona == "opportunistic":
        return fake_sensitive_file()

    elif persona == "advanced_operator":
        return fake_admin_login()

    elif persona == "bot":
        return slow_response()

    else:
        return normal_response()
