import time
import random

class DeceptionEngine:
    def __init__(self):
        # In a real system, this would load the trained QNN model 
        # and predict the persona from the current session features.
        # For this implementation, we simulate the decision based on provided tags.
        pass

    def get_response_strategy(self, persona_label):
        """
        Returns a dictionary of modifications to the response.
        """
        strategy = {
            "delay": 0.0,
            "inject_header": {},
            "inject_body_content": None,
            "status_override": None
        }

        if persona_label == "script_kiddie":
            # Tactic: Frustration / Tarpit
            # Slow down responses to waste their time
            strategy["delay"] = random.uniform(1.0, 5.0)
            strategy["inject_header"] = {"X-Rate-Limit": "100"} # Fake rate limit
            
        elif persona_label == "recon":
            # Tactic: Misdirection
            # Show them a fake admin path to distract them
            strategy["inject_body_content"] = "<!-- DEBUG: Admin panel at /admin_v2_backup -->"
            
        elif persona_label == "apt":
            # Tactic: Canary / Tracking
            # Serve a fake secret that triggers an alert if used elsewhere
            strategy["inject_header"] = {"X-Internal-Token": "canary_token_x882"}
            strategy["inject_body_content"] = '{"secret_config": "db_prod_pass"}'

        return strategy

    def execute_deception(self, strategy):
        # 1. Apply Delay
        if strategy["delay"] > 0:
            time.sleep(strategy["delay"])
            
        # 2. Return other modifiers for the app to use
        return strategy
