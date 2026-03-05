import asyncio
import logging
from app.main import create_app

# Create the app instance at the module level for ASGI servers like Hypercorn/Uvicorn
app = create_app()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("superlive")
    
    logger.info("Starting Superlive 2.0 API Server...")
    
    # Debug: Print registered routes
    logger.info("Registered Routes:")
    for rule in app.url_map.iter_rules():
        logger.info(f" - {rule} -> {rule.endpoint}")

    app.run(host="0.0.0.0", port=5000, debug=True)
