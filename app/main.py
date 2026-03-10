from quart import Quart
from quart_cors import cors
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import httpx
import logging
import asyncio

from app.api.routes.device_routes import device_bp
from app.api.routes.auth_routes import auth_bp
from app.api.routes.user_routes import user_bp
from app.api.routes.livestream_routes import livestream_bp
from app.api.routes.feed_routes import feed_bp
from app.api.routes.discover_routes import discover_bp
from app.api.routes.tempmail_routes import temp_mail_bp
from app.api.routes.auto_gift_routes import auto_gift_bp
from app.api.routes.viewer_routes import viewer_bp
from app.core.logger import setup_logger
from app.core.http_client import SuperliveHttpClient

# Initialize the global application logger
setup_logger()
logger = logging.getLogger("superlive.main")

def create_app():
    import os
    static_dir = os.path.join(os.path.dirname(__file__), "static")
    app = Quart(__name__, static_folder=static_dir, static_url_path="/static")
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
    
    # Initialize Scheduler
    scheduler = AsyncIOScheduler()

    async def keep_alive():
        """Pings the deployment URL to keep the Render instance active."""
        url = "https://freemepvt.onrender.com/api/viewer/health"
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, timeout=10.0)
                logger.info(f"Keep-alive ping sent to {url}. Status: {response.status_code}")
        except Exception as e:
            logger.error(f"Keep-alive ping failed: {e}")

    @app.before_serving
    async def startup():
        # Initialize persistent HTTP client
        from app.services.global_auth_service import GlobalAuthService
        await SuperliveHttpClient.get_client()
        await GlobalAuthService.init_db()
        
        # Start keep-alive scheduler (every 14 minutes)
        scheduler.add_job(keep_alive, 'interval', minutes=14)
        scheduler.start()
        logger.info("APScheduler started: Keep-alive job active every 14 minutes")

    @app.after_serving
    async def shutdown():
        # Shutdown scheduler
        scheduler.shutdown()
        # Close persistent HTTP client
        await SuperliveHttpClient.close_client()
        logger.info("Application shutdown: Cleaned up resources")

    return app

if __name__ == "__main__":
    app = create_app()
    app.run(host="127.0.0.1", port=5000)
