import logging
import httpx
from quart import Blueprint, request, jsonify
from app.services.superlive_service import SuperliveService
from app.core.session_manager import SessionStore

logger = logging.getLogger("superlive.api.feed")

feed_bp = Blueprint("feed", __name__)

@feed_bp.route("/user_posts", methods=["POST"])
async def get_user_posts():
    """
    Exposes POST /feed/user_posts locally.
    Expects 'owner_id'. Optional: 'auth_token', 'limit' (default 15), 'next', 'livestream_id' (for session context).
    """
    try:
        data = await request.get_json()
        if not data or 'owner_id' not in data or 'limit' not in data or 'next' not in data:
            return jsonify({"error": "Missing owner_id, limit, or next"}), 400
            
        proxy_url = data.get("proxy")
        auth_token = data.get("auth_token")
        
        # Resolve session: use existing if auth_token provided, otherwise register fresh device
        if auth_token and auth_token in SessionStore.ACTIVE_USERS:
            session = SessionStore.ACTIVE_USERS[auth_token]
        else:
            logger.info("No active session, registering fresh device for feed lookup...")
            device_res = await SuperliveService.register_device(proxy_url=proxy_url)
            session = {
                "guid": device_res["upstream_response"]["guid"],
                "profile": device_res["device_profile"],
                "domain_config": device_res["domain_config"]
            }
            auth_token = None
            
        domain = session["domain_config"]["origin"]
        
        # Build session_source_url from livestream context if provided
        session_source_url = None
        if data.get("livestream_id"):
            session_source_url = f"{domain}/livestream/{data['livestream_id']}"
        
        logger.info(f"Fetching posts for owner {data['owner_id']} via {domain}...")
        result = await SuperliveService.get_user_posts(
            owner_id=str(data["owner_id"]),
            auth_token=auth_token,
            device_profile=session["profile"],
            domain_config=session["domain_config"],
            device_guid=session["guid"],
            limit=data["limit"],
            next_cursor=data["next"],
            session_source_url=session_source_url,
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
