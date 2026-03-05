import logging
import httpx
import re

logger = logging.getLogger("superlive.modules.tempmail.temply_viewmodel")

class TemplyViewModel:
    BASE_URL = "https://temp.ly/api/emails"

    async def get_inbox(self, username: str, domain: str, client: httpx.AsyncClient = None, proxy_url: str = None):
        """
        Fetch inbox from temp.ly API (works for both temp.ly and temporary.gg)
        If 'client' is provided, it uses the provided client (useful for propagating proxies and headers).
        """
        payload = {
            "username": username,
            "domain": domain
        }
        
        # We only define fallback headers. If the caller provides a client, it should already have its headers configured (e.g. User-Agent).
        # But temp.ly specifically needs some headers.
        fallback_headers = {
            "authority": "temp.ly",
            "accept": "*/*",
            "accept-encoding": "gzip, deflate", 
            "accept-language": "en-US,en;q=0.9",
            "content-type": "application/json",
            "origin": "https://temp.ly",
            "referer": f"https://temp.ly/{username}@{domain}",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36"
        }
        
        # If client is provided, we merge the referer/origin headers into the request, but keep the client's proxy/user-agent if present.
        headers_to_use = fallback_headers.copy()
        if client and "user-agent" in client.headers:
            headers_to_use["user-agent"] = client.headers["user-agent"]

        async def _make_request(http_client):
            try:
                response = await http_client.post(self.BASE_URL, json=payload, headers=headers_to_use)
                response.raise_for_status()
                return response
            except httpx.HTTPStatusError as e:
                logger.error(f"Temp.ly API HTTP error ({e.response.status_code}): {e.response.text}")
                raise Exception(f"Temp.ly API error: {e.response.status_code}")
            except Exception as e:
                logger.error(f"Unexpected Temp.ly error: {e}")
                raise

        if client:
            return await _make_request(client)
        else:
            client_kwargs = {}
            if proxy_url:
                client_kwargs['proxy'] = proxy_url
                
            async with httpx.AsyncClient(**client_kwargs) as new_client:
                return await _make_request(new_client)

    def extract_otp(self, inbox_data: dict) -> str:
        """
        Extract 6-digit OTP from the inbox response data.
        Returns the code if found, else None.
        """
        if not inbox_data or "emails" not in inbox_data:
            return None
            
        emails = inbox_data["emails"]
        if not emails:
            return None
            
        # Look for the verification email
        for email in emails:
            subject = email.get("subject", "")
            sender = email.get("from", "")
            
            # Check if it's from SuperLive
            if "SuperLive" in subject or "SuperLive" in sender:
                body = email.get("body", "")
                
                # Search for 6 digit code in the body
                match = re.search(r'\b(\d{6})\b', body)
                if match:
                    return match.group(1)
                    
        return None

temply_viewmodel = TemplyViewModel()
