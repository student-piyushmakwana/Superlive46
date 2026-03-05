from quart import Quart
from quart_cors import cors
from app.api.routes.device_routes import device_bp
from app.api.routes.auth_routes import auth_bp
from app.api.routes.user_routes import user_bp
from app.api.routes.livestream_routes import livestream_bp
from app.api.routes.feed_routes import feed_bp
from app.api.routes.discover_routes import discover_bp
from app.api.routes.tempmail_routes import temp_mail_bp
from app.api.routes.auto_gift_routes import auto_gift_bp
from app.api.routes.viewer_routes import viewer_bp
import sys
from app.core.logger import setup_logger

# Initialize the global application logger
setup_logger()

def create_app():
    app = Quart(__name__)
    app = cors(app, allow_origin="*") # Enable CORS for all origins
    
    # Register blueprints with modular prefixes
    app.register_blueprint(device_bp, url_prefix="/api/device")
    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(user_bp, url_prefix="/api/users")
    app.register_blueprint(livestream_bp, url_prefix="/api/livestream")
    app.register_blueprint(feed_bp, url_prefix="/api/feed")
    app.register_blueprint(discover_bp, url_prefix="/api/discover")
    app.register_blueprint(temp_mail_bp, url_prefix="/api/tempmail")
    app.register_blueprint(auto_gift_bp, url_prefix="/api/auto/gift")
    app.register_blueprint(viewer_bp, url_prefix="/api/viewer")
    
    @app.before_serving
    async def start_pinger():
        import asyncio
        import httpx
        
        async def pinger():
            async with httpx.AsyncClient() as client:
                while True:
                    await asyncio.sleep(600)  # 10 minutes
                    try:
                        # Self-ping to keep Render alive
                        await client.get("http://127.0.0.1:5000/api/viewer/health")
                    except Exception:
                        pass
        
        app.add_background_task(pinger)

    return app

if __name__ == "__main__":
    app = create_app()
    app.run(host="127.0.0.1", port=5000)
