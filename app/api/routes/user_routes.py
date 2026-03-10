import logging
import httpx
from quart import Blueprint, request, jsonify
from app.services.superlive_service import SuperliveService
from app.core.session_manager import SessionStore

logger = logging.getLogger("superlive.api.users")

user_bp = Blueprint("users", __name__)

@user_bp.route("/verify/update", methods=["POST"])
async def update_profile():
    """
    Exposes POST /users/verify/update locally.
    Expects 'update_data' (e.g. {"name": "Piyush"}) and 'auth_token'.
    """
    try:
        data = await request.get_json()
        if not data or 'update_data' not in data or 'auth_token' not in data:
            return jsonify({"error": "Missing update_data or auth_token"}), 400
            
        auth_token = data["auth_token"]
        if auth_token not in SessionStore.ACTIVE_USERS:
            return jsonify({"error": "Invalid auth_token or session expired."}), 401
            
        proxy_url = data.get("proxy")
        session = SessionStore.ACTIVE_USERS[auth_token]
        
        logger.info(f"Updating profile for user on {session['domain_config']['origin']}...")
        update_res = await SuperliveService.update_profile(
            update_data=data["update_data"],
            auth_token=data["auth_token"],
            device_profile=session["profile"],
            domain_config=session["domain_config"],
            device_guid=session["guid"],
            proxy_url=proxy_url
        )
        
        return jsonify(update_res), 200
        
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

@user_bp.route("/profile", methods=["POST"])
async def get_user_profile():
    """
    Exposes POST /users/profile locally.
    Expects 'user_id'. Optional: 'auth_token', 'livestream_id' (for session context), 'is_from_search'.
    If auth_token is provided, uses the existing session. Otherwise, registers a fresh device on the fly.
    """
    try:
        data = await request.get_json()
        if not data or 'user_id' not in data or 'is_from_search' not in data:
            return jsonify({"error": "Missing user_id or is_from_search"}), 400
            
        proxy_url = data.get("proxy")
        auth_token = data.get("auth_token")
        
        # Resolve session: use existing if auth_token provided, otherwise register fresh device
        if auth_token and auth_token in SessionStore.ACTIVE_USERS:
            session = SessionStore.ACTIVE_USERS[auth_token]
        else:
            logger.info("No active session, registering fresh device for profile lookup...")
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
        
        logger.info(f"Fetching profile for user {data['user_id']} via {domain}...")
        result = await SuperliveService.get_user_profile(
            user_id=str(data["user_id"]),
            auth_token=auth_token,
            device_profile=session["profile"],
            domain_config=session["domain_config"],
            device_guid=session["guid"],
            session_source_url=session_source_url,
            is_from_search=data["is_from_search"],
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

@user_bp.route("/top_gifters", methods=["POST"])
async def get_top_gifters():
    """
    Exposes POST /users/top_gifters locally.
    Expects 'user_id' (int) and 'leaderboard_type' (int). Optional: 'auth_token', 'livestream_id'.
    """
    try:
        data = await request.get_json()
        if not data or 'user_id' not in data or 'leaderboard_type' not in data or 'auth_token' not in data:
            return jsonify({"error": "Missing user_id, leaderboard_type, or auth_token"}), 400
            
        auth_token = data["auth_token"]
        if auth_token not in SessionStore.ACTIVE_USERS:
            return jsonify({"error": "Invalid auth_token or session expired."}), 401
            
        proxy_url = data.get("proxy")
        session = SessionStore.ACTIVE_USERS[auth_token]
            
        domain = session["domain_config"]["origin"]
        
        session_source_url = None
        if data.get("livestream_id"):
            session_source_url = f"{domain}/livestream/{data['livestream_id']}"
        
        logger.info(f"Fetching top gifters for user {data['user_id']} via {domain}...")
        result = await SuperliveService.get_top_gifters(
            user_id=data["user_id"],
            leaderboard_type=data["leaderboard_type"],
            auth_token=auth_token,
            device_profile=session["profile"],
            domain_config=session["domain_config"],
            device_guid=session["guid"],
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

@user_bp.route("/search", methods=["POST"])
async def search_users():
    """
    Exposes POST /users/search locally.
    Expects 'search_query' (or 'query') and optionally 'auth_token'.
    """
    try:
        data = await request.get_json(force=True, silent=True)
        if not data:
            return jsonify({"error": "Missing or invalid JSON body"}), 400
        
        # Accept both 'search_query' and 'query' as field name
        search_query = data.get('search_query') or data.get('query')
        if not search_query:
            return jsonify({"error": "Missing search_query"}), 400
            
        proxy_url = data.get("proxy")
        auth_token = data.get("auth_token")
        
        if auth_token and auth_token in SessionStore.ACTIVE_USERS:
            session = SessionStore.ACTIVE_USERS[auth_token]
        else:
            logger.info("No active session, registering fresh device for search...")
            device_res = await SuperliveService.register_device(proxy_url=proxy_url)
            session = {
                "guid": device_res["upstream_response"]["guid"],
                "profile": device_res["device_profile"],
                "domain_config": device_res["domain_config"]
            }
            auth_token = None
        
        logger.info(f"Searching users for '{search_query}' via {session['domain_config']['origin']}...")
        result = await SuperliveService.search_users(
            search_query=search_query,
            auth_token=auth_token,
            device_profile=session["profile"],
            domain_config=session["domain_config"],
            device_guid=session["guid"],
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

@user_bp.route("/verify/complete", methods=["POST"])
async def complete_profile():
    """
    Exposes POST /users/verify/complete locally.
    Expects 'name', 'gender', 'birthday', and 'auth_token'.
    """
    try:
        data = await request.get_json()
        if not data or 'name' not in data or 'gender' not in data or 'birthday' not in data or 'auth_token' not in data:
            return jsonify({"error": "Missing name, gender, birthday, or auth_token"}), 400
            
        auth_token = data["auth_token"]
        if auth_token not in SessionStore.ACTIVE_USERS:
            return jsonify({"error": "Invalid auth_token or session expired."}), 401
            
        proxy_url = data.get("proxy")
        session = SessionStore.ACTIVE_USERS[auth_token]
        
        logger.info(f"Completing profile for user on {session['domain_config']['origin']}...")
        complete_res = await SuperliveService.complete_profile(
            name=data["name"],
            gender=data["gender"],
            birthday=data["birthday"],
            auth_token=auth_token,
            device_profile=session["profile"],
            domain_config=session["domain_config"],
            device_guid=session["guid"],
            proxy_url=proxy_url
        )
        
        return jsonify(complete_res), 200
        
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

@user_bp.route("/logout", methods=["POST"])
async def logout():
    """
    Exposes POST /users/logout locally.
    Expects 'auth_token'.
    """
    try:
        data = await request.get_json()
        if not data or 'auth_token' not in data:
            return jsonify({"error": "Missing auth_token"}), 400
            
        auth_token = data["auth_token"]
        if auth_token not in SessionStore.ACTIVE_USERS:
            return jsonify({"error": "Invalid auth_token or session expired."}), 401
            
        proxy_url = data.get("proxy")
        session = SessionStore.ACTIVE_USERS[auth_token]
        
        logger.info(f"Logging out user on {session['domain_config']['origin']}...")
        logout_res = await SuperliveService.logout(
            auth_token=auth_token,
            device_profile=session["profile"],
            domain_config=session["domain_config"],
            device_guid=session["guid"],
            proxy_url=proxy_url
        )
        
        # Optionally remove from local session store
        del SessionStore.ACTIVE_USERS[auth_token]
        
        return jsonify(logout_res), 200
        
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

