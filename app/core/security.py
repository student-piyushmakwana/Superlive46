import uuid
import random
import time
import hashlib
import string

def generate_base64_url_safe_string(length=32):
    characters = string.ascii_letters + string.digits + "-_"
    return ''.join(random.choice(characters) for _ in range(length))

class SecurityGenerator:
    """Generates dynamic payloads and identifiers mimicking the official client."""

    @staticmethod
    def generate_device_profile():
        """Creates a unique profile for a device registration."""
        
        # adjust_web_uuid: Standard UUID4 string
        adjust_web_uuid = str(uuid.uuid4())
        
        # installation_id: Standard UUID4 string
        installation_id = str(uuid.uuid4())
        
        # uuid_c1: 32 char URL-safe base64 string
        uuid_c1 = generate_base64_url_safe_string(32)
        
        # adid: 32 char hex string (md5 of uuid_c1 is a safe bet to mimic this format)
        adid = hashlib.md5(uuid_c1.encode()).hexdigest()
        
        # ga_session_id: Unix timestamp-like string starting with 177
        current_time = int(time.time())
        ga_session_id = str(current_time)
        
        # firebase_analytics_id: random 9 digits + dot + timestamp
        firebase_analytics_id = f"{''.join(random.choices(string.digits, k=9))}.{current_time}"
        
        # rtc_id: random 9 digits
        rtc_id = ''.join(random.choices(string.digits, k=9))

        # ttp: The tiktok pixel format, something like 01Kxxxxx.tt.1
        ttp = "01K" + ''.join(random.choices(string.ascii_uppercase + string.digits, k=25)) + "_.tt.1"

        # fbp: Facebook Pixel format
        fbp = f"fb.1.{int(time.time() * 1000)}.{''.join(random.choices(string.digits, k=18))}"

        return {
            "adjust_web_uuid": adjust_web_uuid,
            "installation_id": installation_id,
            "uuid_c1": uuid_c1,
            "adid": adid,
            "ga_session_id": ga_session_id,
            "firebase_analytics_id": firebase_analytics_id,
            "rtc_id": rtc_id,
            "ttp": ttp,
            "fbp": fbp
        }

    @staticmethod
    def get_client_params(device_profile: dict, source_url: str, endpoint_type: str = "register", session_source_url: str = None):
        """Constructs the exact client_params block required by the API, shaped by the origin domain and endpoint type.
        
        Args:
            session_source_url: If provided, overrides session_source_url independently from source_url.
                                Used when the user navigated from a different page (e.g. livestream -> profile).
        """
        adid = device_profile['adid']
        
        # Resolve session_source_url: defaults to source_url if not explicitly provided
        resolved_session_url = session_source_url or source_url
        
        # Base common payload for both domains
        params = {
            "os_type": "web",
            "ad_nationality": None,
            "app_build": "4.5.1",
            "app": "superlive",
            "build_code": "899-2953673-prod",
            "app_language": "en",
            "device_language": "en",
            "device_preferred_languages": ["en-US"],
            "source_url": source_url,
            "session_source_url": resolved_session_url,
            "referrer": "",
            "adjust_web_uuid": device_profile['adjust_web_uuid'],
            "firebase_analytics_id": device_profile.get('firebase_analytics_id'),
            "incognito": True,
            "installation_id": device_profile['installation_id'],
            "rtc_id": device_profile.get('rtc_id'),
            "uuid_c1": device_profile['uuid_c1'],
            "vl_cid": None,
            "ttp": device_profile['ttp'],
            "twclid": None,
            "tdcid": None,
            "fbc": None,
            "ga_session_id": device_profile['ga_session_id'],
            "web_type": 1
        }
        
        # If signup endpoint, provide everything (adid + adjust + fbp + firebase + rtc) regardless of domain
        if endpoint_type == "signup":
            params["adid"] = adid
            params["adjust_attribution_data"] = {
                "adid": adid,
                "tracker_token": "mii5ej6",
                "tracker_name": "Organic",
                "network": "Organic"
            }
            params["fbp"] = device_profile.get("fbp")

        # Otherwise, shape by domain for regular device registration
        else:
            # Delete signup-only fields for register
            if "firebase_analytics_id" in params:
                params["firebase_analytics_id"] = None
            if "rtc_id" in params:
               del params["rtc_id"]

            # Superlivetv.com, superlivechat.tv, and superlive24.com format
            if any(domain in source_url for domain in ["superlivetv.com", "superlivechat.tv", "superlive24.com"]):
                params["adjust_attribution_data"] = None
                params["fbp"] = device_profile.get("fbp")
                # No 'adid' at the root level for these payloads
            
            # Superlive.chat format
            else:
                params["adid"] = adid
                params["adjust_attribution_data"] = {
                    "adid": adid,
                    "tracker_token": "mii5ej6",
                    "tracker_name": "Organic",
                    "network": "Organic"
                }
                params["fbp"] = None

        return params
