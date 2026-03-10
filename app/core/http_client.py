import httpx
import logging
import asyncio
from typing import Optional
from app.core.config import config

logger = logging.getLogger("superlive.http_client")

class SuperliveHttpClient:
    """Manages a persistent AsyncClient session for efficient upstream communication."""
    
    _client: Optional[httpx.AsyncClient] = None
    _lock = asyncio.Lock()

    @classmethod
    async def get_client(cls) -> httpx.AsyncClient:
        """Returns the global persistent client, initializing if necessary."""
        if cls._client is None or cls._client.is_closed:
            async with cls._lock:
                if cls._client is None or cls._client.is_closed:
                    cls._client = httpx.AsyncClient(
                        timeout=config.REQUEST_TIMEOUT,
                        # Better defaults for a proxy service
                        limits=httpx.Limits(max_keepalive_connections=20, max_connections=100),
                        follow_redirects=True
                    )
                    logger.info("Initialized persistent HTTPX AsyncClient")
        return cls._client

    @classmethod
    async def close_client(cls):
        """Closes the persistent client session."""
        if cls._client and not cls._client.is_closed:
            await cls._client.aclose()
            logger.info("Closed persistent HTTPX AsyncClient")

    @staticmethod
    def construct_headers(domain_config: dict, device_id: str = None, auth_token: str = None):
        """Constructs headers mirroring the Chrome Web Client for the given origin config."""
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
        """Sends a POST request to Superlive using the persistent client."""
        api_base = domain_config["api_base"]
        url = f"{api_base.rstrip('/')}/{endpoint.lstrip('/')}"
            
        headers = cls.construct_headers(domain_config, device_id=device_id, auth_token=auth_token)

        # Requests with proxies still require a separate client instance in httpx 
        if proxy_url:
            async with httpx.AsyncClient(proxy=proxy_url, timeout=config.REQUEST_TIMEOUT, headers=headers) as proxy_client:
                try:
                    response = await proxy_client.post(url, json=json_data)
                    response.raise_for_status()
                    return response
                except httpx.HTTPStatusError as e:
                    status = e.response.status_code
                    try:
                        body = e.response.json()
                    except Exception:
                        body = e.response.text
                    logger.error(f"Upstream HTTP Error {status}: {body}")
                    raise RuntimeError(f"Upstream returned HTTP {status}: {body}") from None
                except Exception as e:
                    logger.error(f"Proxy Request Failed: {e}")
                    raise

        # Use persistent client, reset if in bad state
        max_retries = 2
        for attempt in range(max_retries):
            try:
                client = await cls.get_client()
                response = await client.post(url, json=json_data, headers=headers)
                response.raise_for_status()
                return response
            except httpx.HTTPStatusError as e:
                status = e.response.status_code
                try:
                    body = e.response.json()
                except Exception:
                    body = e.response.text
                logger.error(f"Upstream HTTP Error {status}: {body}")
                raise RuntimeError(f"Upstream returned HTTP {status}: {body}") from None
            except (httpx.RemoteProtocolError, httpx.ConnectError, httpx.ReadError) as e:
                logger.warning(f"Connection error on attempt {attempt + 1}: {e}. Resetting client...")
                # Force client reset on connection errors
                async with cls._lock:
                    if cls._client and not cls._client.is_closed:
                        await cls._client.aclose()
                    cls._client = None
                if attempt == max_retries - 1:
                    raise RuntimeError(f"Connection failed after {max_retries} attempts: {e}") from None
            except Exception as e:
                logger.error(f"HTTP Request Failed: {e}")
                raise
