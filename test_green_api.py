#!/usr/bin/env python3
"""Test script to verify Green API configuration."""

import asyncio
import logging
import sys
from config import settings
from green_api_client import GreenAPIClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def test_green_api():
    """Test Green API connection and basic functionality."""
    logger.info("🧪 Testing Green API configuration...")
    
    # Check if Green API credentials are configured
    if not settings.green_api_instance_id or not settings.green_api_token:
        logger.error("❌ Green API credentials not configured!")
        logger.error("Please set GREEN_API_INSTANCE_ID and GREEN_API_TOKEN environment variables")
        return False
    
    logger.info(f"✅ Green API Instance ID: {settings.green_api_instance_id}")
    logger.info(f"✅ Green API Token: {'*' * len(settings.green_api_token)}")
    
    try:
        # Initialize Green API client
        logger.info("🔧 Initializing Green API client...")
        client = GreenAPIClient(None)  # No message handler needed for this test
        logger.info("✅ Green API client initialized successfully")
        
        # Test sending a message (optional - comment out if you don't want to send test message)
        test_phone = settings.summary_recipient_phone
        if test_phone:
            logger.info(f"📤 Testing message send to {test_phone}...")
            try:
                client.send_message(
                    phone=test_phone,
                    message="🧪 Test message from WhatsApp Groups Monitor (Green API)"
                )
                logger.info("✅ Test message sent successfully!")
            except Exception as e:
                logger.warning(f"⚠️ Could not send test message: {e}")
                logger.info("This might be normal if the instance is not ready yet")
        
        logger.info("🎉 Green API test completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Green API test failed: {e}")
        return False


if __name__ == "__main__":
    success = asyncio.run(test_green_api())
    sys.exit(0 if success else 1)
