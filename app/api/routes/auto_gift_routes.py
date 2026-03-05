import logging
from quart import Blueprint, request, jsonify, render_template
from app.modules.gift.gift_orchestrator import gift_orchestrator

logger = logging.getLogger("superlive.modules.gift.routes")

auto_gift_bp = Blueprint("auto_gift", __name__)

@auto_gift_bp.route('/', methods=['GET', 'POST'])
async def auto_gift():
    """
    GET: Renders stream_viewer.html
    POST: Exposes POST /api/auto/gift locally to start or stop the auto-gift loop.
    Expects 'code' (10 to start, 12 to stop).
    Optional params: 'livestream_id', 'worker', 'use_proxy', 'proxies'.
    """
    if request.method == 'GET':
        return await render_template('viewer.html')

    try:
        req_data = await request.get_json()
        if not req_data:
            return jsonify({"error": "Missing JSON body"}), 400
            
        code = req_data.get('code')
        
        if code == 12:
            logger.info("Received Stop Signal (Code 12)")
            success, message = gift_orchestrator.stop_loop()
            return jsonify({"message": message}), 200

        if code == 10:
            livestream_id = req_data.get('livestream_id') or 127902815
            worker_count = req_data.get('worker', 2)
            use_proxy = req_data.get('use_proxy', True)
            custom_proxies = req_data.get('proxies')
            
            success, message = gift_orchestrator.start_loop(
                livestream_id=livestream_id, 
                worker_count=worker_count, 
                use_proxy=use_proxy, 
                proxies=custom_proxies
            )
            
            if success:
                return jsonify({"message": f"Auto gift loop started with {worker_count} workers (Proxy: {use_proxy})"}), 200
            else:
                return jsonify({"message": message}), 200
            
        return jsonify({"error": "Invalid code. Use 10 to start, 12 to stop."}), 400
        
    except Exception as e:
        logger.error(f"Auto gift route error: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500
