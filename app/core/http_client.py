import httpx
import logging
from app.core.config import config

logger = logging.getLogger("superlive.http_client")

class SuperliveHttpClient:
    """Manages requests to the Superlive upstream API with correct headers."""

    @staticmethod
    def construct_headers(domain_config: dict, device_id: str = None, auth_token: str = None):
        """Constructs headers specifically mirroring the Chrome Web Client for the given origin config."""
        origin = domain_config["origin"]
        headers = {
            "authority": domain_config["authority"],
            "accept": "application/json",
            "accept-encoding": "gzip, deflate, br, zstd",
            "accept-language": "en-US,en;q=0.9",
            "content-type": "application/json",
            "origin": origin,
            "priority": "u=1, i",
            "referer": origin if origin.endswith('/') else f"{origin}/",
            "sec-ch-ua": "\"Not:A-Brand\";v=\"99\", \"Google Chrome\";v=\"145\", \"Chromium\";v=\"145\"",
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": "\"Windows\"",
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": domain_config["sec_fetch_site"],
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36"
        }
        
        if device_id:
            headers["device-id"] = device_id
            
        if auth_token:
            headers["authorization"] = f"Token {auth_token}"
            
        return headers

    @classmethod
    async def post(cls, endpoint: str, json_data: dict, domain_config: dict, proxy_url: str = None, device_id: str = None, auth_token: str = None) -> httpx.Response:
        """Sends a POST request to Superlive."""
        # Ensure api_base doesn't have a trailing slash if endpoint has a leading slash
        api_base = domain_config["api_base"]
        if api_base.endswith('/') and endpoint.startswith('/'):
            url = f"{api_base[:-1]}{endpoint}"
        else:
            url = f"{api_base}{endpoint}"
            
        headers = cls.construct_headers(domain_config, device_id=device_id, auth_token=auth_token)
        
        # Configure client kwargs
        client_kwargs = {
            "headers": headers,
            "timeout": config.REQUEST_TIMEOUT
        }
        
        if proxy_url:
            client_kwargs["proxy"] = proxy_url
            
        async with httpx.AsyncClient(**client_kwargs) as client:
            try:
                response = await client.post(url, json=json_data)
                response.raise_for_status()
                return response
            except httpx.HTTPStatusError as e:
                logger.error(f"HTTP Return Error {e.response.status_code}: {e.response.text}")
                raise e
            except Exception as e:
                logger.error(f"HTTP Request Failed: {e}")
                raise e
