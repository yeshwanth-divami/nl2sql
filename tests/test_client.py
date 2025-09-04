#!/usr/bin/env python3
"""
Test client to test the ChatService endpoint.
"""

import httpx
import asyncio
import json

async def test_chat_endpoint():
    """Test the chat endpoint."""
    base_url = "http://localhost:8000"
    
    async with httpx.AsyncClient() as client:
        # Test health check
        print("1. Testing health endpoint...")
        try:
            response = await client.get(f"{base_url}/health")
            print(f"   Status: {response.status_code}")
            print(f"   Response: {response.json()}")
        except Exception as e:
            print(f"   Error: {e}")
            return
        
        # Test config endpoint
        print("\n2. Testing config endpoint...")
        try:
            response = await client.get(f"{base_url}/config")
            print(f"   Status: {response.status_code}")
            print(f"   Response: {json.dumps(response.json(), indent=2)}")
        except Exception as e:
            print(f"   Error: {e}")
        
        # Test chat endpoint
        print("\n3. Testing chat endpoint...")
        test_payload = {
            "prompt": "Hello, how are you?",
            "assistant_id": "16"
        }
        
        try:
            response = await client.post(
                f"{base_url}/chat",
                json=test_payload,
                timeout=30.0
            )
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                result = response.json()
                print(f"   Response: {json.dumps(result, indent=2)}")
            else:
                print(f"   Error Response: {response.text}")
        except Exception as e:
            print(f"   Error: {e}")

def main():
    """Run the test client."""
    print("Testing NL2SQL Chat API...")
    print("Make sure the server is running on http://localhost:8000")
    print("-" * 50)
    
    asyncio.run(test_chat_endpoint())

if __name__ == "__main__":
    main()
