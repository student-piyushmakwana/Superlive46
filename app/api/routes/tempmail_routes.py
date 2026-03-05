import logging
from quart import Blueprint, request, jsonify
from app.modules.tempmail.temply_viewmodel import temply_viewmodel
from app.modules.tempmail.temply_tracker import temply_tracker
import random

logger = logging.getLogger("superlive.modules.tempmail")

temp_mail_bp = Blueprint("tempmail", __name__)

DOMAINS = ["temp.ly"]

@temp_mail_bp.route('/email', methods=['GET'])
async def get_email():
    """
    Generate a new random username and domain combination and save it to the tracker.
    Returns: {"username": "<str>", "domain": "<str>", "email": "<str>"}
    """
    try:
        username = temply_tracker.generate_username()
        domain = random.choice(DOMAINS)
        email = f"{username}@{domain}"
        
        return jsonify({
            "username": username,
            "domain": domain,
            "email": email
        }), 200
        
    except Exception as e:
        logger.error(f"Get email route error: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@temp_mail_bp.route('/otp', methods=['GET', 'POST'])
async def get_otp():
    """
    Check the inbox for the given username and domain and extract the OTP.
    Accepts GET query params (username=<str>&domain=<str>) or 
    POST JSON body ({"username": "<str>", "domain": "<str>"})
    """
    try:
        username = None
        domain = None
        proxy_url = None
        
        if request.method == 'POST':
            if request.is_json:
                data = await request.get_json()
                if data:
                    username = data.get('username')
                    domain = data.get('domain')
                    proxy_url = data.get('proxy')
            else:
                # Fallback for form data if needed
                form = await request.form
                username = form.get('username')
                domain = form.get('domain')
                
        # Fallback to args if POST didn't have them, or if it's a GET request
        if not username:
            username = request.args.get('username')
        if not domain:
            domain = request.args.get('domain')
        
        if not username or not domain:
            return jsonify({"error": "Missing 'username' or 'domain' parameter"}), 400
            
        if domain not in DOMAINS:
            return jsonify({"error": f"Invalid domain. Supported domains are: {DOMAINS}"}), 400

        upstream_response = await temply_viewmodel.get_inbox(username, domain, proxy_url=proxy_url)
        inbox_data = upstream_response.json()
        otp = temply_viewmodel.extract_otp(inbox_data)
        
        if otp:
            return jsonify({"success": True, "otp": otp}), 200
        else:
            return jsonify({"success": False, "message": "OTP not found in inbox"}), 404
            
    except Exception as e:
        logger.error(f"Get OTP route error: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500
