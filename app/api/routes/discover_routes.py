import logging
import httpx
from quart import Blueprint, request, jsonify
from app.services.superlive_service import SuperliveService
from app.core.session_manager import SessionStore

logger = logging.getLogger("superlive.api.discover")

discover_bp = Blueprint("discover", __name__)

@discover_bp.route("/", methods=["POST"])
async def discover():
    """
    Exposes POST /api/discover locally.
    Optional: 'auth_token', 'next', 'type' (default 0), 'proxy'.
    """
    try:
        data = await request.get_json() or {}
        
        proxy_url = data.get("proxy")
        auth_token = data.get("auth_token")
        next_cursor = data.get("next")
        type_val = data.get("type", 0)
        
        # Resolve session
        if auth_token and auth_token in SessionStore.ACTIVE_USERS:
            session = SessionStore.ACTIVE_USERS[auth_token]
        else:
            logger.info("No active session, registering fresh device for discover...")
            device_res = await SuperliveService.register_device(proxy_url=proxy_url)
            session = {
                "guid": device_res["upstream_response"]["guid"],
                "profile": device_res["device_profile"],
                "domain_config": device_res["domain_config"]
            }
            auth_token = None
            
        domain = session["domain_config"]["origin"]
        
        logger.info(f"Fetching discover feed via {domain}...")
        result = await SuperliveService.get_discover(
            auth_token=auth_token,
            device_profile=session["profile"],
            domain_config=session["domain_config"],
            device_guid=session["guid"],
            next_cursor=next_cursor,
            type_val=type_val,
            proxy_url=proxy_url
        )
        
        return jsonify(result), 200
        
    except httpx.HTTPStatusError as e:
        logger.error(f"Upstream HTTP Error: {e.response.text}")
        return jsonify({
            "error": "Upstream API Error", 
            "status_code": e.response.status_code, 
            "details": e.response.text
        }), e.response.status_code
    except Exception as e:
        logger.error(f"Internal Route Error: {e}")
        return jsonify({"error": str(e)}), 500
