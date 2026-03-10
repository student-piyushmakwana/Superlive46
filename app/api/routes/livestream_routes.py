import logging
import httpx
from quart import Blueprint, request, jsonify
from app.services.superlive_service import SuperliveService
from app.core.session_manager import SessionStore
from app.services.global_auth_service import GlobalAuthService

logger = logging.getLogger("superlive.api.livestream")

livestream_bp = Blueprint("livestream", __name__)

@livestream_bp.route("/retrieve", methods=["POST"])
async def retrieve_livestream():
    """
    Exposes POST /livestream/retrieve locally.
    Expects 'livestream_id'. 'auth_token' is optional.
    If auth_token is missing, uses the global MongoDB-backed token to allow private stream access.
    """
    try:
        data = await request.get_json()
        if not data or 'livestream_id' not in data:
            return jsonify({"error": "Missing livestream_id"}), 400
            
        proxy_url = data.get("proxy")
        auth_token = data.get("auth_token")

        if auth_token and auth_token in SessionStore.ACTIVE_USERS:
            session = SessionStore.ACTIVE_USERS[auth_token]
            domain = session["domain_config"]["origin"]
            
            logger.info(f"Retrieving livestream {data['livestream_id']} via {domain} (User Auth)...")
            result = await SuperliveService.retrieve_livestream(
                livestream_id=str(data["livestream_id"]),
                auth_token=auth_token,
                device_profile=session["profile"],
                domain_config=session["domain_config"],
                device_guid=session["guid"],
                proxy_url=proxy_url
            )
            return jsonify(result), 200
            
        # Global Auth Fallback
        logger.info("No user session, attempting Global Auth fallback for private livestream retrieve...")
        
        for attempt in range(2):
            if attempt == 0:
                global_token, global_session = await GlobalAuthService.get_valid_auth_token()
            else:
                logger.info("Retrying with a freshly minted global auth token...")
                global_token, global_session = await GlobalAuthService.force_refresh_token()
                
            if not global_token or not global_session:
                # If we absolutely cannot get a global token, fallback to anonymous device registration
                logger.warning("Global auth unavailable. Falling back to anonymous retrieve...")
                device_res = await SuperliveService.register_device(proxy_url=proxy_url)
                global_session = {
                    "guid": device_res["upstream_response"]["guid"],
                    "profile": device_res["device_profile"],
                    "domain_config": device_res["domain_config"]
                }
                global_token = None
                attempt = 1 # Prevent further retries on anonymous fail
                
            domain = global_session["domain_config"]["origin"]
            logger.info(f"Retrieving livestream {data['livestream_id']} via {domain} (Global Auth Attempt {attempt+1})...")
            
            try:
                result = await SuperliveService.retrieve_livestream(
                    livestream_id=str(data["livestream_id"]),
                    auth_token=global_token,
                    device_profile=global_session["profile"],
                    domain_config=global_session["domain_config"],
                    device_guid=global_session["guid"],
                    proxy_url=proxy_url
                )
                
                if result.get("upstream_response") is None and attempt == 0:
                    logger.warning("Global Auth token failed (upstream_response is null). Invalidating and retrying...")
                    continue
                    
                return jsonify(result), 200
                
            except RuntimeError as e:
                # Upstream returned an HTTP error (e.g. 401/403 for expired token)
                if attempt == 0 and global_token:
                    logger.warning(f"Global Auth token rejected by upstream: {e}. Invalidating and retrying...")
                    continue
                # If we still fail on attempt 2 or as anonymous, raise to outer block
                raise

        return jsonify({"error": "Failed to retrieve stream after retries"}), 500
        
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

@livestream_bp.route("/chat/send_gift", methods=["POST"])
async def send_gift():
    """
    Exposes POST /livestream/chat/send_gift locally.
    Expects 'livestream_id', 'gift_id', 'user_ids', 'guids', 'auth_token'.
    Optional: 'gift_context', 'gift_batch_size', 'tip_gift_id'.
    """
    try:
        data = await request.get_json()
        required_fields = ['livestream_id', 'auth_token']
        if not data or not all(k in data for k in required_fields):
            return jsonify({"error": f"Missing one or more required fields: {required_fields}"}), 400
            
        auth_token = data["auth_token"]
        if auth_token not in SessionStore.ACTIVE_USERS:
            return jsonify({"error": "Invalid auth_token or session expired."}), 401
            
        proxy_url = data.get("proxy")
        session = SessionStore.ACTIVE_USERS[auth_token]
        
        import uuid
        guids = data.get("guids", [str(uuid.uuid4())])
        gift_id = data.get("gift_id", 5141) # Default to Rose (5141)
        user_ids = data.get("user_ids", [])
        
        logger.info(f"Sending gift {gift_id} to livestream {data['livestream_id']} via {session['domain_config']['origin']}...")
        result = await SuperliveService.send_gift(
            livestream_id=data["livestream_id"],
            gift_id=gift_id,
            user_ids=user_ids,
            guids=guids,
            auth_token=auth_token,
            device_profile=session["profile"],
            domain_config=session["domain_config"],
            device_guid=session["guid"],
            gift_context=data.get("gift_context", 1),
            gift_batch_size=data.get("gift_batch_size", 1),
            tip_gift_id=data.get("tip_gift_id"),
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

@livestream_bp.route("/active_viewers_and_top_gifters", methods=["POST"])
async def active_viewers_and_top_gifters():
    """
    Exposes POST /livestream/active_viewers_and_top_gifters locally.
    Expects 'livestream_id'.
    Optional: 'auth_token', 'active_viewers_next', 'top_gifters_next'.
    """
    try:
        data = await request.get_json()
        if not data or 'livestream_id' not in data:
            return jsonify({"error": "Missing livestream_id"}), 400
            
        proxy_url = data.get("proxy")
        auth_token = data.get("auth_token")
        
        # Resolve session: use existing if auth_token provided, otherwise register fresh device
        if auth_token and auth_token in SessionStore.ACTIVE_USERS:
            session = SessionStore.ACTIVE_USERS[auth_token]
        else:
            logger.info("No active session, registering fresh device for active viewers lookup...")
            device_res = await SuperliveService.register_device(proxy_url=proxy_url)
            session = {
                "guid": device_res["upstream_response"]["guid"],
                "profile": device_res["device_profile"],
                "domain_config": device_res["domain_config"]
            }
            auth_token = None
            
        domain = session["domain_config"]["origin"]
        
        logger.info(f"Fetching active viewers & top gifters for livestream {data['livestream_id']} via {domain}...")
        result = await SuperliveService.get_active_viewers_and_top_gifters(
            livestream_id=str(data["livestream_id"]),
            auth_token=auth_token,
            device_profile=session["profile"],
            domain_config=session["domain_config"],
            device_guid=session["guid"],
            active_viewers_next=data.get("active_viewers_next"),
            top_gifters_next=data.get("top_gifters_next"),
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
