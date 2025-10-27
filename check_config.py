#!/usr/bin/env python3
"""Check current configuration."""

import os
from config import settings

def check_config():
    """Display current configuration."""
    print("🔧 WhatsApp Groups Monitor Configuration")
    print("=" * 50)
    
    # Green API Configuration
    print("\n📱 Green API Configuration:")
    print(f"  Instance ID: {settings.green_api_instance_id or 'NOT SET'}")
    print(f"  Token: {'*' * len(settings.green_api_token) if settings.green_api_token else 'NOT SET'}")
    
    # Database Configuration
    print("\n🗄️ Database Configuration:")
    print(f"  URL: {settings.database_url}")
    
    # Google Gemini Configuration
    print("\n🤖 Google Gemini Configuration:")
    print(f"  API Key: {'*' * len(settings.google_api_key) if settings.google_api_key else 'NOT SET'}")
    print(f"  Model: {settings.gemini_llm_model}")
    
    # Notification Configuration
    print("\n📬 Notification Configuration:")
    print(f"  Summary Recipient: {settings.summary_recipient_phone}")
    print(f"  Schedule Hour: {settings.summary_schedule_hour}:00")
    print(f"  Timezone: {settings.summary_schedule_timezone}")
    
    # Environment Variables
    print("\n🌍 Environment Variables:")
    env_vars = [
        "GREEN_API_INSTANCE_ID",
        "GREEN_API_TOKEN", 
        "DATABASE_URL",
        "GOOGLE_API_KEY",
        "SUMMARY_RECIPIENT_PHONE"
    ]
    
    for var in env_vars:
        value = os.getenv(var)
        if value:
            if "TOKEN" in var or "KEY" in var:
                print(f"  {var}: {'*' * len(value)}")
            else:
                print(f"  {var}: {value}")
        else:
            print(f"  {var}: NOT SET")
    
    print("\n" + "=" * 50)
    
    # Check if Green API is properly configured
    if settings.green_api_instance_id and settings.green_api_token:
        print("✅ Green API appears to be configured")
    else:
        print("❌ Green API is not properly configured")
        print("   Please set GREEN_API_INSTANCE_ID and GREEN_API_TOKEN")

if __name__ == "__main__":
    check_config()
