import logging
import httpx
from quart import Blueprint, request, jsonify, render_template
from app.services.superlive_service import SuperliveService
from app.core.session_manager import SessionStore

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
    Registers a temporary device anonymous session if needed.
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
        
        logger.info(f"Fetching stream info for {livestream_id}...")
        
        # Register a temporary device to get an anonymous context
        device_res = await SuperliveService.register_device(proxy_url=proxy_url)
        
        # Fetch stream details
        stream_result = await SuperliveService.retrieve_livestream(
            livestream_id=livestream_id,
            auth_token=None,
            device_profile=device_res["device_profile"],
            domain_config=device_res["domain_config"],
            device_guid=device_res["upstream_response"]["guid"],
            proxy_url=proxy_url
        )
        
        if "upstream_response" in stream_result:
            return jsonify({
                "status": "success",
                "stream_details": stream_result["upstream_response"].get("stream_details"),
                "user": stream_result["upstream_response"].get("user"),
                "agora_app_id": "466f7443143a3df42868339f73e53887" # Potential App ID from traces
            }), 200
        else:
            return jsonify(stream_result), 200
            
    except httpx.HTTPStatusError as e:
        logger.error(f"Upstream HTTP Error: {e.response.text}")
        return jsonify({
            "error": "Upstream API Error", 
            "status_code": e.response.status_code
        }), e.response.status_code
    except Exception as e:
        logger.error(f"Viewer route error: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500
