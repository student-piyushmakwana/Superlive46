import os
import secrets
import logging
from dotenv import load_dotenv

load_dotenv()

LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

logging.getLogger("asyncio").setLevel(logging.ERROR)

class Config:
    DOMAINS = [
        {
            "origin": "https://superlive.chat",
            "api_base": "https://api.spl-web.link/api/web",
            "authority": "api.spl-web.link",
            "sec_fetch_site": "cross-site",
            "payload_type": "v1"
        },
        {
            "origin": "https://superlivetv.com",
            "api_base": "https://api.spl-web.link/api/web",
            "authority": "api.spl-web.link",
            "sec_fetch_site": "cross-site",
            "payload_type": "v2"
        },
        {
            "origin": "https://superlivechat.tv",
            "api_base": "https://api.superlivechat.tv/api/web",
            "authority": "api.superlivechat.tv",
            "sec_fetch_site": "same-site",
            "payload_type": "v2"
        },
        {
            "origin": "https://superlive24.com",
            "api_base": "https://api.superlive24.com/api/web",
            "authority": "api.superlive24.com",
            "sec_fetch_site": "same-site",
            "payload_type": "v2"
        }
    ]
    APP_BUILD = "4.5.1"
    BUILD_CODE = "899-2953673-prod"
    REQUEST_TIMEOUT = 30

config = Config()
