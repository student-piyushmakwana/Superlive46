import asyncio
from app.main import create_app
import logging

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("superlive")
    
    logger.info("Starting Superlive 2.0 API Server...")
    app = create_app()
    
    # Debug: Print registered routes
    logger.info("Registered Routes:")
    for rule in app.url_map.iter_rules():
        logger.info(f" - {rule} -> {rule.endpoint}")

    app.run(host="0.0.0.0", port=5000, debug=True)
