import subprocess
import time
import os
import signal
import sys

def run_honeypot():
    print("[*] Starting Honeypot...")
    # Start process in new window/detached if possible, or just background
    # On Windows, creationflags=subprocess.CREATE_NEW_CONSOLE might help if we wanted to see it,
    # but for automation we keep it hidden.
    return subprocess.Popen([sys.executable, "-m", "uvicorn", "honeypot.app:app", "--port", "8000"])

def run_persona(mode, duration):
    print(f"[*] Running Persona: {mode} for {duration}s...")
    subprocess.run([sys.executable, "simulator/persona_bot.py", "--mode", mode, "--duration", str(duration)])

def main():
    honeypot_process = run_honeypot()
    
    # Wait for startup
    time.sleep(3)
    
    try:
        # Generate balanced dataset
        personas = ["benign", "script_kiddie", "recon", "apt"]
        for p in personas:
            run_persona(p, duration=15) # 15s each for quick test
            time.sleep(1)
            
        print("[*] Data Generation Complete.")
        
    finally:
        print("[*] Stopping Honeypot...")
        honeypot_process.terminate()
        try:
            honeypot_process.wait(timeout=5)
        except:
            honeypot_process.kill()

if __name__ == "__main__":
    main()
