import os
import json
import pandas as pd
import numpy as np
from glob import glob

LOG_DIR = "data/raw_logs"
OUTPUT_FILE = "data/processed/features.csv"

def compute_entropy(s):
    if not s: return 0
    prob = [s.count(c) / len(s) for c in set(s)]
    return -sum(p * np.log2(p) for p in prob)

def extract_features():
    print("Loading logs...")
    files = glob(os.path.join(LOG_DIR, "*.json"))
    logs = []
    
    for f in files:
        try:
            with open(f, 'r') as file:
                logs.append(json.load(file))
        except:
            pass
            
    if not logs:
        print("No logs found.")
        return

    df = pd.DataFrame(logs)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    # Simple Sessionization: Group by Client IP (Since we ran one persona at a time per IP in sim)
    # In real world, we'd use time windows (e.g., 5 min sessions)
    sessions = []
    
    grouped = df.groupby('client_ip')
    
    for ip, group in grouped:
        group = group.sort_values('timestamp')
        
        # Calculate Inter-arrival times
        time_diffs = group['timestamp'].diff().dt.total_seconds().fillna(0)
        
        # Feature 1: Request Count
        req_count = len(group)
        
        # Feature 2: Burstiness (Std Dev of time diffs)
        burst_rate = time_diffs.std() if len(time_diffs) > 1 else 0
        
        # Feature 3: Error Rate
        errors = len(group[group['status_code'] >= 400])
        error_rate = errors / req_count
        
        # Feature 4: Unique Paths
        unique_paths = group['path'].nunique()
        
        # Feature 5: IDOR Index (Are IDs sequential?)
        # Filter for /user/{id}
        has_idor_ids = []
        for path in group['path']:
            if path.startswith("/user/"):
                try:
                    uid = int(path.split("/")[-1])
                    has_idor_ids.append(uid)
                except:
                    pass
        
        idor_seq_score = 0
        if len(has_idor_ids) > 1:
            diffs = np.diff(sorted(has_idor_ids))
            # Ratio of diffs that are == 1 (Sequential)
            seq_steps = np.sum(diffs == 1)
            idor_seq_score = seq_steps / len(diffs)

        # Label from the logs (Taking the most common tag in the session to be robust)
        tags = group['persona_tag'].mode()
        label = tags[0] if not tags.empty else "Unknown"
        
        sessions.append({
            "client_ip": ip,
            "req_count": req_count,
            "burst_rate": burst_rate,
            "error_rate": error_rate,
            "unique_paths": unique_paths,
            "idor_seq_score": idor_seq_score,
            "label": label 
        })
        
    final_df = pd.DataFrame(sessions)
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    final_df.to_csv(OUTPUT_FILE, index=False)
    print(f"Features extracted to {OUTPUT_FILE}")
    return final_df

if __name__ == "__main__":
    extract_features()
