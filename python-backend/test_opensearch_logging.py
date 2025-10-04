#!/usr/bin/env python3
"""
OpenSearch Logging Test
"""
import os
import sys
import asyncio
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

print("=" * 60)
print("🔍 OpenSearch Logging Configuration Test")
print("=" * 60)
print()

# Check environment variables
print("📋 Environment Variables:")
print(f"  ENABLE_OPENSEARCH_LOGGING = {os.getenv('ENABLE_OPENSEARCH_LOGGING')}")
print(f"  OPENSEARCH_URL = {os.getenv('OPENSEARCH_URL')}")
print(f"  TEAM_NAME = {os.getenv('TEAM_NAME')}")
print(f"  LOG_LEVEL = {os.getenv('LOG_LEVEL')}")
print()

# Test logger import
print("📦 Testing logger import...")
try:
    from app.core.logging import logger
    print("  ✅ Logger imported successfully")
except Exception as e:
    print(f"  ❌ Logger import failed: {e}")
    sys.exit(1)

print()

# Test basic logging
print("📝 Testing basic logging...")
logger.info("Test INFO log")
logger.warning("Test WARNING log")
logger.error("Test ERROR log")
print("  ✅ Basic logging works")
print()

# Test structured logging
print("📊 Testing structured logging...")
logger.info(
    "Test structured log",
    extra={
        "event": "test_event",
        "user_id": "test-user",
        "session_id": "test-session-123",
        "metric": "test_metric",
        "value": 42
    }
)
print("  ✅ Structured logging works")
print()

# Test OpenSearch handler manually
print("🌐 Testing OpenSearch handler...")
try:
    import httpx
    opensearch_url = os.getenv('OPENSEARCH_URL')
    team_name = os.getenv('TEAM_NAME', 'wegathon')
    
    async def test_opensearch():
        log_entry = {
            "team": team_name,
            "user": "test-script",
            "action": "test",
            "message": "Test log from Python script",
            "level": "INFO",
            "service": "wegathon-backend-test"
        }
        
        ingest_url = f"{opensearch_url}/teams-ingest-pipeline/ingest"
        print(f"  Sending to: {ingest_url}")
        print(f"  Data: {log_entry}")
        
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(
                ingest_url,
                json=[log_entry],
                headers={"Content-Type": "application/json"}
            )
            return response.status_code, response.text
    
    status_code, response_text = asyncio.run(test_opensearch())
    print(f"  Response: {status_code} - {response_text}")
    
    if status_code == 200:
        print("  ✅ OpenSearch connection successful!")
    else:
        print(f"  ⚠️  Unexpected response: {status_code}")
        
except Exception as e:
    print(f"  ❌ OpenSearch test failed: {e}")
    import traceback
    traceback.print_exc()

print()
print("=" * 60)
print("🎯 Test completed!")
print("=" * 60)
print()
print("📊 Next Steps:")
print("  1. Check if logs appear in backend console")
print("  2. Wait 1-2 minutes for logs to reach OpenSearch")
print("  3. Check OpenSearch Discover at:")
print("     https://wegathon-opensearch.uzlas.com/app/discover#/")
print("  4. Look for index pattern: 'teams-*' or create if missing")
print()

