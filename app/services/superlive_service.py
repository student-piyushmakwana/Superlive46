import random
from app.core.http_client import SuperliveHttpClient
from app.core.security import SecurityGenerator
from app.core.config import config

class SuperliveService:
    """Business logic for interacting with Superlive Upstream API"""

    @staticmethod
    async def register_device(proxy_url: str = None) -> dict:
        """
        Generates a unique device profile, formats the client_params,
        and posts it to /device/register. Returns the exact response.
        """
        # 1. Generate unique fake device profile
        device_profile = SecurityGenerator.generate_device_profile()
        
        # 1.5 Select a random domain
        domain_config = random.choice(config.DOMAINS)
        domain = domain_config["origin"]
        
        # 2. Build the exact payload
        client_params = SecurityGenerator.get_client_params(device_profile, source_url=f"{domain}/")
        payload = {
            "client_params": client_params
        }
        
        # 3. Send Request
        response = await SuperliveHttpClient.post(
            endpoint="/device/register",
            json_data=payload,
            domain_config=domain_config,
            proxy_url=proxy_url
        )
        
        # Return Both the Response AND the generated device profile so we can re-use it
        return {
            "status": "success",
            "device_profile": device_profile,
            "domain_config": domain_config,
            "upstream_response": response.json()
        }

    @staticmethod
    async def request_email_otp(email: str, device_profile: dict, domain_config: dict, device_guid: str, proxy_url: str = None, force_new: bool = False) -> dict:
        """
        Requests an OTP verification code to be sent to the given email address.
        """
        domain = domain_config["origin"]
        client_params = SecurityGenerator.get_client_params(device_profile, source_url=f"{domain}/", endpoint_type="signup")
        
        payload = {
            "client_params": client_params,
            "email": email,
            "force_new": force_new
        }
        
        response = await SuperliveHttpClient.post(
            endpoint="/signup/send_email_verification_code",
            json_data=payload,
            domain_config=domain_config,
            proxy_url=proxy_url,
            device_id=device_guid
        )
        
        return {
            "status": "success",
            "upstream_response": response.json()
        }

    @staticmethod
    async def verify_email_otp(verification_id: int, code: int, device_profile: dict, domain_config: dict, device_guid: str, proxy_url: str = None) -> dict:
        """
        Submits the 6-digit OTP code to verify the email address before final signup.
        """
        domain = domain_config["origin"]
        client_params = SecurityGenerator.get_client_params(device_profile, source_url=f"{domain}/", endpoint_type="signup")
        
        payload = {
            "client_params": client_params,
            "email_verification_id": verification_id,
            "code": code
        }
        
        response = await SuperliveHttpClient.post(
            endpoint="/signup/verify_email",
            json_data=payload,
            domain_config=domain_config,
            proxy_url=proxy_url,
            device_id=device_guid
        )
        
        return {
            "status": "success",
            "upstream_response": response.json()
        }

    @staticmethod
    async def signup_email(email: str, password: str, device_profile: dict, domain_config: dict, device_guid: str, proxy_url: str = None) -> dict:
        """
        Signs up a new user via email using an existing device profile and assigned domain.
        Injects the device_guid into the request header.
        """
        domain = domain_config["origin"]
        
        # Build the exact payload for the 'signup' endpoint
        client_params = SecurityGenerator.get_client_params(device_profile, source_url=f"{domain}/", endpoint_type="signup")
        
        payload = {
            "client_params": client_params,
            "email": email,
            "password": password
        }
        
        response = await SuperliveHttpClient.post(
            endpoint="/signup/email",
            json_data=payload,
            domain_config=domain_config,
            proxy_url=proxy_url,
            device_id=device_guid
        )
        
        return {
            "status": "success",
            "device_profile": device_profile,
            "domain_config": domain_config,
            "upstream_response": response.json()
        }

    @staticmethod
    async def update_profile(update_data: dict, auth_token: str, device_profile: dict, domain_config: dict, device_guid: str, proxy_url: str = None) -> dict:
        """
        Updates the user's profile information (e.g. name).
        Requires the JWT/auth token received from the signup/login stage.
        """
        domain = domain_config["origin"]
        # The update endpoint typically uses /discover but keeps identical device trace structure
        client_params = SecurityGenerator.get_client_params(device_profile, source_url=f"{domain}/discover", endpoint_type="signup")
        
        payload = {
            "client_params": client_params,
            "update_data": update_data
        }
        
        response = await SuperliveHttpClient.post(
            endpoint="/users/verify/update",
            json_data=payload,
            domain_config=domain_config,
            proxy_url=proxy_url,
            device_id=device_guid,
            auth_token=auth_token
        )
        
        return {
            "status": "success",
            "upstream_response": response.json()
        }

    @staticmethod
    async def login_email(email: str, password: str, device_profile: dict, domain_config: dict, device_guid: str, proxy_url: str = None) -> dict:
        """
        Logs in an existing user via email and password using an assigned domain and profile.
        Injects the device_guid into the request header.
        """
        domain = domain_config["origin"]
        
        # Build the exact payload for the 'email_signin' endpoint
        # Uses endpoint_type="signup" to maintain the inclusion of fbp, rtc_id, etc.
        client_params = SecurityGenerator.get_client_params(device_profile, source_url=f"{domain}/", endpoint_type="signup")
        
        payload = {
            "client_params": client_params,
            "email": email,
            "password": password
        }
        
        response = await SuperliveHttpClient.post(
            endpoint="/signup/email_signin",
            json_data=payload,
            domain_config=domain_config,
            proxy_url=proxy_url,
            device_id=device_guid
        )
        
        return {
            "status": "success",
            "device_profile": device_profile,
            "domain_config": domain_config,
            "upstream_response": response.json()
        }

    @staticmethod
    async def retrieve_livestream(livestream_id: str, auth_token: str, device_profile: dict, domain_config: dict, device_guid: str, proxy_url: str = None) -> dict:
        """
        Retrieves livestream data for a given livestream_id.
        The source_url is set to {origin}/livestream/{livestream_id} to mimic browser navigation.
        """
        domain = domain_config["origin"]
        client_params = SecurityGenerator.get_client_params(device_profile, source_url=f"{domain}/livestream/{livestream_id}", endpoint_type="signup")
        
        payload = {
            "client_params": client_params,
            "livestream_id": livestream_id
        }
        
        response = await SuperliveHttpClient.post(
            endpoint="/livestream/retrieve",
            json_data=payload,
            domain_config=domain_config,
            proxy_url=proxy_url,
            device_id=device_guid,
            auth_token=auth_token
        )
        
        return {
            "status": "success",
            "upstream_response": response.json()
        }

    @staticmethod
    async def get_user_profile(user_id: str, auth_token: str, device_profile: dict, domain_config: dict, device_guid: str, session_source_url: str = None, is_from_search: bool = False, proxy_url: str = None) -> dict:
        """
        Fetches a user's profile by user_id.
        source_url is set to {origin}/profile/{user_id} (with ?isFromSearch=true if from search).
        session_source_url reflects where the user navigated from (e.g. a livestream or search page).
        """
        domain = domain_config["origin"]
        
        # Append ?isFromSearch=true to source_url when navigating from search
        source_url = f"{domain}/profile/{user_id}"
        if is_from_search:
            source_url = f"{source_url}?isFromSearch=true"
            # Default session_source_url to search page if not explicitly provided
            if not session_source_url:
                session_source_url = f"{domain}/search"
        
        client_params = SecurityGenerator.get_client_params(
            device_profile,
            source_url=source_url,
            endpoint_type="signup",
            session_source_url=session_source_url
        )
        
        payload = {
            "client_params": client_params,
            "user_id": user_id,
            "is_from_search": is_from_search
        }
        
        response = await SuperliveHttpClient.post(
            endpoint="/users/profile",
            json_data=payload,
            domain_config=domain_config,
            proxy_url=proxy_url,
            device_id=device_guid,
            auth_token=auth_token
        )
        
        return {
            "status": "success",
            "upstream_response": response.json()
        }

    @staticmethod
    async def get_user_posts(owner_id: str, auth_token: str, device_profile: dict, domain_config: dict, device_guid: str, limit: int = 15, next_cursor: str = None, session_source_url: str = None, proxy_url: str = None) -> dict:
        """
        Fetches a user's posts/feed by owner_id.
        source_url is set to {origin}/profile/{owner_id}.
        """
        domain = domain_config["origin"]
        client_params = SecurityGenerator.get_client_params(
            device_profile,
            source_url=f"{domain}/profile/{owner_id}",
            endpoint_type="signup",
            session_source_url=session_source_url
        )
        
        payload = {
            "client_params": client_params,
            "owner_id": owner_id,
            "limit": limit,
            "next": next_cursor
        }
        
        response = await SuperliveHttpClient.post(
            endpoint="/feed/user_posts",
            json_data=payload,
            domain_config=domain_config,
            proxy_url=proxy_url,
            device_id=device_guid,
            auth_token=auth_token
        )
        
        return {
            "status": "success",
            "upstream_response": response.json()
        }

    @staticmethod
    async def get_top_gifters(user_id: int, leaderboard_type: int, auth_token: str, device_profile: dict, domain_config: dict, device_guid: str, session_source_url: str = None, proxy_url: str = None) -> dict:
        """
        Fetches the top gifters leaderboard for a given user.
        source_url is set to {origin}/profile/{user_id}.
        """
        domain = domain_config["origin"]
        client_params = SecurityGenerator.get_client_params(
            device_profile,
            source_url=f"{domain}/profile/{user_id}",
            endpoint_type="signup",
            session_source_url=session_source_url
        )
        
        payload = {
            "client_params": client_params,
            "user_id": user_id,
            "leaderboard_type": leaderboard_type
        }
        
        response = await SuperliveHttpClient.post(
            endpoint="/user/top_gifters",
            json_data=payload,
            domain_config=domain_config,
            proxy_url=proxy_url,
            device_id=device_guid,
            auth_token=auth_token
        )
        
        return {
            "status": "success",
            "upstream_response": response.json()
        }

    @staticmethod
    async def search_users(search_query: str, auth_token: str, device_profile: dict, domain_config: dict, device_guid: str, proxy_url: str = None) -> dict:
        """
        Searches for users by query string.
        source_url is set to {origin}/search.
        """
        domain = domain_config["origin"]
        client_params = SecurityGenerator.get_client_params(
            device_profile,
            source_url=f"{domain}/search",
            endpoint_type="signup"
        )
        
        payload = {
            "client_params": client_params,
            "search_query": search_query
        }
        
        response = await SuperliveHttpClient.post(
            endpoint="/users/search",
            json_data=payload,
            domain_config=domain_config,
            proxy_url=proxy_url,
            device_id=device_guid,
            auth_token=auth_token
        )
        
        return {
            "status": "success",
            "upstream_response": response.json()
        }

    @staticmethod
    async def complete_profile(name: str, gender: int, birthday: int, auth_token: str, device_profile: dict, domain_config: dict, device_guid: str, proxy_url: str = None) -> dict:
        """
        Final profile completion step sending name, gender, and birthday (ms timestamp) directly in the root payload.
        """
        domain = domain_config["origin"]
        client_params = SecurityGenerator.get_client_params(device_profile, source_url=f"{domain}/discover", endpoint_type="signup")
        
        payload = {
            "client_params": client_params,
            "name": name,
            "gender": gender,
            "birthday": birthday
        }
        
        response = await SuperliveHttpClient.post(
            endpoint="/users/update",
            json_data=payload,
            domain_config=domain_config,
            proxy_url=proxy_url,
            device_id=device_guid,
            auth_token=auth_token
        )
        
        return {
            "status": "success",
            "upstream_response": response.json()
        }

    @staticmethod
    async def get_discover(auth_token: str, device_profile: dict, domain_config: dict, device_guid: str, next_cursor: str = None, type_val: int = 0, proxy_url: str = None) -> dict:
        """
        Fetches the discover feed.
        source_url is set to {origin}/discover.
        session_source_url is set to {origin}/discover.
        """
        domain = domain_config["origin"]
        client_params = SecurityGenerator.get_client_params(
            device_profile,
            source_url=f"{domain}/discover",
            endpoint_type="signup",
            session_source_url=f"{domain}/discover"
        )
        
        payload = {
            "client_params": client_params,
            "next": next_cursor,
            "type": type_val
        }
        
        response = await SuperliveHttpClient.post(
            endpoint="/discover",
            json_data=payload,
            domain_config=domain_config,
            proxy_url=proxy_url,
            device_id=device_guid,
            auth_token=auth_token
        )
        
        return {
            "status": "success",
            "upstream_response": response.json()
        }

    @staticmethod
    async def send_gift(livestream_id: int, gift_id: int, user_ids: list, guids: list, auth_token: str, device_profile: dict, domain_config: dict, device_guid: str, gift_context: int = 1, gift_batch_size: int = 1, tip_gift_id: int = None, proxy_url: str = None) -> dict:
        """
        Sends a gift during a livestream.
        source_url and session_source_url are set to {origin}/livestream/{livestream_id}.
        """
        domain = domain_config["origin"]
        client_params = SecurityGenerator.get_client_params(
            device_profile,
            source_url=f"{domain}/livestream/{livestream_id}",
            endpoint_type="signup",
            session_source_url=f"{domain}/livestream/{livestream_id}"
        )
        
        payload = {
            "client_params": client_params,
            "gift_context": gift_context,
            "livestream_id": livestream_id,
            "gift_id": gift_id,
            "guids": guids,
            "gift_batch_size": gift_batch_size,
            "tip_gift_id": tip_gift_id,
            "user_ids": user_ids
        }
        
        response = await SuperliveHttpClient.post(
            endpoint="/livestream/chat/send_gift",
            json_data=payload,
            domain_config=domain_config,
            proxy_url=proxy_url,
            device_id=device_guid,
            auth_token=auth_token
        )
        
        return {
            "status": "success",
            "upstream_response": response.json()
        }

    @staticmethod
    async def get_active_viewers_and_top_gifters(livestream_id: str, auth_token: str, device_profile: dict, domain_config: dict, device_guid: str, active_viewers_next: str = None, top_gifters_next: str = None, proxy_url: str = None) -> dict:
        """
        Fetches the active viewers and top gifters for a livestream.
        source_url and session_source_url are set to {origin}/livestream/{livestream_id}.
        """
        domain = domain_config["origin"]
        client_params = SecurityGenerator.get_client_params(
            device_profile,
            source_url=f"{domain}/livestream/{livestream_id}",
            endpoint_type="signup",
            session_source_url=f"{domain}/livestream/{livestream_id}"
        )
        
        payload = {
            "client_params": client_params,
            "livestream_id": livestream_id,
            "active_viewers_next": active_viewers_next,
            "top_gifters_next": top_gifters_next
        }
        
        response = await SuperliveHttpClient.post(
            endpoint="/livestream/active_viewers_and_top_gifters",
            json_data=payload,
            domain_config=domain_config,
            proxy_url=proxy_url,
            device_id=device_guid,
            auth_token=auth_token
        )
        
        return {
            "status": "success",
            "upstream_response": response.json()
        }

    @staticmethod
    async def logout(auth_token: str, device_profile: dict, domain_config: dict, device_guid: str, proxy_url: str = None) -> dict:
        """
        Logs out the user from the upstream server.
        source_url is set to {origin}/discover.
        session_source_url is set to {origin}/logout.
        """
        domain = domain_config["origin"]
        client_params = SecurityGenerator.get_client_params(
            device_profile,
            source_url=f"{domain}/discover",
            endpoint_type="signup",
            session_source_url=f"{domain}/logout"
        )
        
        payload = {
            "client_params": client_params
        }
        
        response = await SuperliveHttpClient.post(
            endpoint="/user/logout",
            json_data=payload,
            domain_config=domain_config,
            proxy_url=proxy_url,
            device_id=device_guid,
            auth_token=auth_token
        )
        
        return {
            "status": "success",
            "upstream_response": response.json()
        }
