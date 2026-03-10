import logging
import httpx
from quart import Blueprint, request, jsonify, render_template
from app.services.superlive_service import SuperliveService
from app.core.session_manager import SessionStore
from app.services.global_auth_service import GlobalAuthService

logger = logging.getLogger("superlive.api.viewer")

viewer_bp = Blueprint("viewer", __name__, template_folder="../templates")

@viewer_bp.route("/", methods=["GET"])
async def index():
    """Renders the dedicated Material 3 Stream Viewer page."""
    return await render_template("viewer.html")

@viewer_bp.route("/health")
async def health():
    import time
    return {"status": "ok", "timestamp": time.time()}

@viewer_bp.route("/stream_info", methods=["POST"])
async def get_stream_info():
    """
    Fetches stream details for a given livestream_id.
    Uses the global auth token to ensure private streams are accessible.
    """
    try:
        logger.info("--- Entering get_stream_info ---")
        data = await request.get_json()
        logger.info(f"Request data: {data}")
        
        if not data or 'livestream_id' not in data:
            logger.warning("Missing livestream_id in request")
            return jsonify({"error": "Missing livestream_id"}), 400
            
        livestream_id = str(data["livestream_id"])
        proxy_url = data.get("proxy")
        
        logger.info(f"Fetching stream info for {livestream_id} using global auth...")
        
        for attempt in range(2):
            if attempt == 0:
                global_token, global_session = await GlobalAuthService.get_valid_auth_token()
            else:
                global_token, global_session = await GlobalAuthService.force_refresh_token()
                
            if not global_token or not global_session:
                # Fallback to anonymous
                device_res = await SuperliveService.register_device(proxy_url=proxy_url)
                global_session = {
                    "guid": device_res["upstream_response"]["guid"],
                    "profile": device_res["device_profile"],
                    "domain_config": device_res["domain_config"]
                }
                global_token = None
                break
                
            try:
                stream_result = await SuperliveService.retrieve_livestream(
                    livestream_id=livestream_id,
                    auth_token=global_token,
                    device_profile=global_session["profile"],
                    domain_config=global_session["domain_config"],
                    device_guid=global_session["guid"],
                    proxy_url=proxy_url
                )
                
                if stream_result.get("upstream_response") is None and attempt == 0:
                    logger.warning("Global Auth token failed (upstream_response is null). Invalidating and retrying...")
                    continue
                    
                break
                
            except RuntimeError as e:
                # Upstream returned an HTTP error (e.g. 401/403 for expired token)
                if attempt == 0 and global_token:
                    logger.warning(f"Global Viewer token rejected by upstream: {e}. Invalidating and retrying...")
                    continue
                raise
        
        if stream_result and "upstream_response" in stream_result and stream_result["upstream_response"]:
            return jsonify({
                "status": "success",
                "stream_details": stream_result["upstream_response"].get("stream_details"),
                "user": stream_result["upstream_response"].get("user"),
                "agora_app_id": "466f7443143a3df42868339f73e53887" # Potential App ID from traces
            }), 200
        else:
            return jsonify(stream_result), 200
            
    except Exception as e:
        logger.error(f"Viewer route error: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500
