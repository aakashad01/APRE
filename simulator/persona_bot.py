import asyncio
import httpx
import random
import argparse
from faker import Faker

fake = Faker()
BASE_URL = "http://localhost:8000"

# Common User Agents
UA_NORMAL = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
UA_SCANNER = "Mozilla/5.0 (compatible; Nmap Scripting Engine; https://nmap.org/book/nse.html)"
UA_APT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Safari/605.1.15"

class PersonaBot:
    def __init__(self, mode):
        self.mode = mode
        self.client = httpx.AsyncClient(timeout=5.0)

    async def run(self, duration_seconds=30):
        print(f"[*] Starting Persona: {self.mode.upper()}")
        end_time = asyncio.get_event_loop().time() + duration_seconds
        
        while asyncio.get_event_loop().time() < end_time:
            if self.mode == "benign":
                await self.behavior_benign()
            elif self.mode == "script_kiddie":
                await self.behavior_script_kiddie()
            elif self.mode == "recon":
                await self.behavior_recon()
            elif self.mode == "apt":
                await self.behavior_apt()
            
            # Sleep based on persona speed
            sleep_time = self.get_sleep_time()
            await asyncio.sleep(sleep_time)

    def get_sleep_time(self):
        if self.mode == "script_kiddie": return random.uniform(0.1, 0.5) # Fast
        if self.mode == "benign": return random.uniform(1.0, 3.0) # Normal
        if self.mode == "recon": return random.uniform(0.5, 1.5) # Methodical
        if self.mode == "apt": return random.uniform(2.0, 5.0) # Slow/Stealth
        return 1.0

    async def behavior_benign(self):
        # Normal user: visits home, logs in (maybe fails once), views own profile
        headers = {"User-Agent": UA_NORMAL, "X-Persona-Tag": "benign"}
        # 80% chance to fetch own profile (1002 is 'Bob User')
        if random.random() < 0.8:
            await self.client.get(f"{BASE_URL}/user/1002", headers=headers)
        else:
            await self.client.get(f"{BASE_URL}/", headers=headers)

    async def behavior_script_kiddie(self):
        # Noisy, brute force, random IDs
        headers = {"User-Agent": random.choice([UA_NORMAL, "Python-urllib/3.8"])}
        action = random.choice(["idor_random", "login_brute"])
        
        if action == "idor_random":
            # Random large IDs
            rand_id = random.randint(1000, 9999)
            await self.client.get(f"{BASE_URL}/user/{rand_id}", headers=headers)
        elif action == "login_brute":
            creds = {"username": "admin", "password": fake.password()}
            await self.client.post(f"{BASE_URL}/login", json=creds, headers=headers)

    async def behavior_recon(self):
        # Sequential scanning, checking for admin
        headers = {"User-Agent": UA_NORMAL}
        
        # 1. Sequential IDOR
        start_id = 1000 + random.randint(0, 5) # Start somewhere near valid range
        for i in range(3): # Do a small burst of sequential requests
            await self.client.get(f"{BASE_URL}/user/{start_id + i}", headers=headers)
            
        # 2. Check risky paths
        if random.random() < 0.3:
            await self.client.get(f"{BASE_URL}/admin", headers=headers)

    async def behavior_apt(self):
        # Targeted SSRF, specific headers, low volume
        headers = {"User-Agent": UA_APT, "X-Custom-Header": "Internal-Test"}
        
        # Try to hit AWS metadata or internal service
        targets = ["http://169.254.169.254/latest/meta-data/", "http://localhost:8000/admin"]
        target = random.choice(targets)
        
        await self.client.get(f"{BASE_URL}/fetch?url={target}", headers=headers)

async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", type=str, required=True, choices=["benign", "script_kiddie", "recon", "apt"])
    parser.add_argument("--duration", type=int, default=10)
    args = parser.parse_args()
    
    bot = PersonaBot(args.mode)
    await bot.run(args.duration)

if __name__ == "__main__":
    asyncio.run(main())
