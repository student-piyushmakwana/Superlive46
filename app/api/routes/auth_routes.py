from quart import Blueprint, jsonify, request
from app.services.superlive_service import SuperliveService
from app.core.session_manager import SessionStore
import httpx
import logging

logger = logging.getLogger("superlive.api.auth")

auth_bp = Blueprint("auth", __name__)

# Temporary in-memory store for keeping device sessions alive during the 3-step signup flow.
# In a production environment, this should be backed by Redis or a Database.
# Key: email -> Value: {"device_session": {...}, "verification_id": 1234}
AUTH_SESSIONS = {}

@auth_bp.route("/signup/request-otp", methods=["POST"])
async def request_otp():
    """
    Exposes POST /auth/signup/request-otp locally.
    Registers new device and requests OTP.
    Saves the session state internally.
    """
    try:
        data = await request.get_json()
        if not data or 'email' not in data:
            return jsonify({"error": "Missing email"}), 400
            
        email = data["email"]
        proxy_url = data.get("proxy")
        
        # 1. Register Device
        logger.info(f"Registering new virtual device for OTP request...")
        device_res = await SuperliveService.register_device(proxy_url=proxy_url)
        guid = device_res["upstream_response"]["guid"]
        device_profile = device_res["device_profile"]
        domain_config = device_res["domain_config"]
        
        # 2. Request OTP
        logger.info(f"Requesting OTP for {email} via {domain_config['origin']}...")
        otp_res = await SuperliveService.request_email_otp(
            email=email,
            device_profile=device_profile,
            domain_config=domain_config,
            device_guid=guid,
            proxy_url=proxy_url
        )
        
        # 3. Store in Session
        verification_id = otp_res["upstream_response"].get("email_verification_id")
        SessionStore.PENDING_SIGNUPS[email] = {
            "device_session": {
                "guid": guid,
                "profile": device_profile,
                "domain_config": domain_config
            },
            "verification_id": verification_id
        }
        
        return jsonify({
            "status": "success",
            "message": f"OTP requested for {email}. Proceed to /verify-otp",
            "email_verification_id": verification_id
        }), 200
        
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

@auth_bp.route("/signup/verify-otp", methods=["POST"])
async def verify_otp():
    """
    Exposes POST /auth/signup/verify-otp locally.
    Expects 'email' and 'code'.
    """
    try:
        data = await request.get_json()
        if not data or 'email' not in data or 'code' not in data:
            return jsonify({"error": "Missing email or code"}), 400
            
        email = data["email"]
        if email not in SessionStore.PENDING_SIGNUPS:
            return jsonify({"error": "No active session found for this email. Request OTP first."}), 404
            
        session_data = SessionStore.PENDING_SIGNUPS[email]
        session = session_data["device_session"]
        verification_id = session_data["verification_id"]
        proxy_url = data.get("proxy")
        
        logger.info(f"Verifying OTP {data['code']} for verification request {verification_id}...")
        verify_res = await SuperliveService.verify_email_otp(
            verification_id=verification_id,
            code=data["code"],
            device_profile=session["profile"],
            domain_config=session["domain_config"],
            device_guid=session["guid"],
            proxy_url=proxy_url
        )
        
        return jsonify(verify_res), 200
        
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

@auth_bp.route("/signup/email", methods=["POST"])
async def signup_email():
    """
    Exposes POST /auth/signup/email locally.
    Expects JSON payload with 'email', 'password'.
    """
    try:
        data = await request.get_json()
        if not data or 'email' not in data or 'password' not in data:
            return jsonify({"error": "Missing email or password"}), 400
            
        email = data["email"]
        if email not in SessionStore.PENDING_SIGNUPS:
            return jsonify({"error": "No active session found for this email. Request OTP first."}), 404
            
        session = SessionStore.PENDING_SIGNUPS[email]["device_session"]
        proxy_url = data.get("proxy")
        
        logger.info(f"Targeting Auth Server {session['domain_config']['origin']} with GUID {session['guid']}...")
        signup_res = await SuperliveService.signup_email(
            email=email,
            password=data["password"],
            device_profile=session["profile"],
            domain_config=session["domain_config"],
            device_guid=session["guid"],
            proxy_url=proxy_url
        )
        
        # Cleanup session upon successful signup and transition to active
        if signup_res.get("status") == "success":
            up_res = signup_res.get("upstream_response", {})
            auth_token = up_res.get("token") or up_res.get("auth_token") or up_res.get("access_token")
            
            if auth_token:
                logger.info(f"Successfully migrated {email} to Active User context.")
                SessionStore.ACTIVE_USERS[auth_token] = session
            
            del SessionStore.PENDING_SIGNUPS[email]
            
        return jsonify(signup_res), 200
        
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

@auth_bp.route("/login/email", methods=["POST"])
async def login_email():
    """
    Exposes POST /auth/login/email locally.
    Expects JSON payload with 'email', 'password'.
    Registers a new virtual device context on the fly and logs in.
    """
    try:
        data = await request.get_json()
        if not data or 'email' not in data or 'password' not in data:
            return jsonify({"error": "Missing email or password"}), 400
            
        email = data["email"]
        password = data["password"]
        proxy_url = data.get("proxy")
        
        # 1. Register a new device context specifically for this login session
        logger.info(f"Registering fresh virtual device for login of {email}...")
        device_res = await SuperliveService.register_device(proxy_url=proxy_url)
        guid = device_res["upstream_response"]["guid"]
        device_profile = device_res["device_profile"]
        domain_config = device_res["domain_config"]
        
        # 2. Execute Login
        logger.info(f"Logging in {email} via {domain_config['origin']} with GUID {guid}...")
        login_res = await SuperliveService.login_email(
            email=email,
            password=password,
            device_profile=device_profile,
            domain_config=domain_config,
            device_guid=guid,
            proxy_url=proxy_url
        )
        
        # 3. Store valid session for Profile actions
        if login_res.get("status") == "success":
            up_res = login_res.get("upstream_response", {})
            auth_token = up_res.get("token") or up_res.get("auth_token") or up_res.get("access_token")
            
            if auth_token:
                logger.info(f"Successfully logged in and generated session token for {email}.")
                SessionStore.ACTIVE_USERS[auth_token] = {
                    "guid": guid,
                    "profile": device_profile,
                    "domain_config": domain_config
                }
                
        return jsonify(login_res), 200
        
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
