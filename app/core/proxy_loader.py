import os
import random

PROXY_FILE = os.path.join(os.path.dirname(__file__), "..", "..", "proxy.txt")

def load_proxies():
    """
    Reads proxy.txt and returns a shuffled list of proxies formatted as httpx URLs.
    Handles ip:port:user:pass formatting.
    """
    proxy_path = os.path.abspath(PROXY_FILE)
    if not os.path.exists(proxy_path):
        return []

    proxies = []
    with open(proxy_path, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            
            parts = line.split(":")
            if len(parts) == 4:
                ip, port, user, pwd = parts
                proxies.append(f"http://{user}:{pwd}@{ip}:{port}")
            elif len(parts) == 2:
                ip, port = parts
                proxies.append(f"http://{ip}:{port}")
    
    # Shuffle so workers don't always pick the same top proxy first
    random.shuffle(proxies)
    return proxies

def get_random_proxy():
    """Utility to quickly grab one random proxy."""
    proxies = load_proxies()
    return random.choice(proxies) if proxies else None
