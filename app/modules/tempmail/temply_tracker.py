import json
import os
import random
import string
import logging

logger = logging.getLogger("superlive.modules.tempmail.temply_tracker")

class TemplyTracker:
    def __init__(self, filepath: str = None):
        if filepath is None:
            # Default to the same directory as this script
            base_dir = os.path.dirname(os.path.abspath(__file__))
            self.filepath = os.path.join(base_dir, "temply_used_usernames.json")
        else:
            self.filepath = filepath
        
        self.used_usernames = self._load_usernames()

    def _load_usernames(self) -> set:
        """Load used usernames from the JSON file."""
        if not os.path.exists(self.filepath):
            return set()
        
        try:
            with open(self.filepath, 'r') as f:
                data = json.load(f)
                if isinstance(data, list):
                    return set(data)
                return set()
        except Exception as e:
            logger.error(f"Failed to load used usernames from {self.filepath}: {e}")
            return set()

    def _save_usernames(self):
        """Save the current set of used usernames to the JSON file."""
        try:
            with open(self.filepath, 'w') as f:
                json.dump(list(self.used_usernames), f, indent=4)
        except Exception as e:
            logger.error(f"Failed to save used usernames to {self.filepath}: {e}")

    def generate_username(self, length: int = 16) -> str:
        """
        Generate a unique random alphanumeric username of the specified length 
        that has not been used before.
        """
        characters = string.ascii_lowercase + string.digits
        
        while True:
            # Generate random string
            new_username = ''.join(random.choice(characters) for _ in range(length))
            
            # Check if it's unique
            if new_username not in self.used_usernames:
                self.used_usernames.add(new_username)
                self._save_usernames()
                return new_username

# Singleton instance
temply_tracker = TemplyTracker()
