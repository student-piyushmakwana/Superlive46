import asyncio
import logging
import random
from typing import Optional, Dict

from app.services.superlive_service import SuperliveService

logger = logging.getLogger("superlive.services.global_auth")

class GlobalAuthService:
    """
    Manages a single global authenticated session for the entire application.
    Fetches random accounts from a hardcoded list, logs them in, and caches the auth_token.
    This token is injected into requests that require authentication but lack a user session.
    """
    
    _ACCOUNTS = [
        {"email": "origin.ukrain@atomicmail.io", "password": "Piyush@123"},
        {"email": "origin.lebanon@atomicmail.io", "password": "Piyush@123"},
        {"email": "origin.piyush@atomicmail.io", "password": "Piyush@123"},
        {"email": "rajat@ibolinva.com", "password": "piyush1234"},
        {"email": "piyush.india@atomicmail.io", "password": "Piyush@123"},
        {"email": "india.piyush@atomicmail.io", "password": "Piyush@123"}
    ]
    
    # Global cached token and proxy
    _cached_auth_token: Optional[str] = None
    
    # We store the associated device profile so we can make identical follow-up requests
    _device_session: Optional[Dict] = None

    _lock = asyncio.Lock()

    @classmethod
    async def init_db(cls):
        """Deprecated: No longer using MongoDB. Kept for backwards compatibility with main.py startup."""
        logger.info("GlobalAuthService: Using hardcoded accounts list. No DB to initialize.")
        pass

    @classmethod
    async def get_valid_auth_token(cls) -> Optional[tuple[str, dict]]:
        """
        Returns (auth_token, session_dict).
        If no valid token is cached, fetches a new one from the hardcoded list and logs in.
        session_dict contains: {"guid": ..., "profile": ..., "domain_config": ...}
        """
        async with cls._lock:
            if cls._cached_auth_token and cls._device_session:
                return cls._cached_auth_token, cls._device_session
            
            logger.info("No global auth token found. Fetching via a hardcoded account...")
            return await cls._refresh_token_unlocked()

    @classmethod
    async def force_refresh_token(cls) -> Optional[tuple[str, dict]]:
        """Invalidate the current token and force a new login."""
        async with cls._lock:
            logger.info("Forcing refresh of global auth token...")
            return await cls._refresh_token_unlocked()

    @classmethod
    async def _refresh_token_unlocked(cls) -> Optional[tuple[str, dict]]:
        try:
            # 1. Fetch a random unused account from list
            account = random.choice(cls._ACCOUNTS)
            email = account["email"]
            password = account["password"]
            
            logger.info(f"Selected hardcoded account {email}. Logging into Superlive...")

            # 2. Register Device Session first
            device_res = await SuperliveService.register_device()
            if device_res["status"] != "success":
                logger.error("Failed to register device for global auth.")
                return None, None
                
            session_dict = {
                "guid": device_res["upstream_response"]["guid"],
                "profile": device_res["device_profile"],
                "domain_config": device_res["domain_config"]
            }

            # 3. Log In
            login_res = await SuperliveService.login_email(
                email=email,
                password=password,
                device_profile=session_dict["profile"],
                domain_config=session_dict["domain_config"],
                device_guid=session_dict["guid"]
            )
            
            upstream = login_res.get("upstream_response", {})
            auth_token = upstream.get("token")
            
            if not auth_token:
                logger.error(f"Login failed for {email}: {login_res}")
                return None, None
                
            # 4. Success! Cache it globally
            logger.info(f"Successfully minted global auth token from account {email}")
            cls._cached_auth_token = auth_token
            cls._device_session = session_dict
            
            # Add to local SessionStore so local endpoints (e.g. /api/users/logout) recognize it
            from app.core.session_manager import SessionStore
            SessionStore.ACTIVE_USERS[auth_token] = session_dict
            
            return cls._cached_auth_token, cls._device_session
            
        except Exception as e:
            logger.error(f"Error refreshing global token: {e}", exc_info=True)
            return None, None
