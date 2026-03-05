from quart import Blueprint, jsonify, request
from app.services.superlive_service import SuperliveService
import httpx
import logging

logger = logging.getLogger("superlive.api.device")

device_bp = Blueprint("device", __name__)

@device_bp.route("/register", methods=["POST"])
async def register_device():
    """
    Exposes POST /device/register locally.
    Accepts optional {"proxy": "http://..."} JSON payload to route upstream.
    """
    try:
        data = {}
        if request.is_json:
            data = await request.get_json()
            
        proxy_url = data.get("proxy") if data else None
        
        result = await SuperliveService.register_device(proxy_url=proxy_url)
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
