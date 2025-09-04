#!/usr/bin/env python3
"""
Test script to run the FastAPI server and test the ChatService endpoint.
"""

import uvicorn
import os
import sys
from pathlib import Path

# Add the src directory to Python path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

def main():
    """Run the FastAPI server."""
    # Set environment variables for testing (you'll need to replace these with actual values)
    os.environ.setdefault('AUTH_TOKEN', 'your-auth-token-here')
    os.environ.setdefault('LLM_MODEL_PROVIDER', 'openai')
    os.environ.setdefault('LLM_MODEL_VERSION', 'gpt-4')
    
    print("Starting NL2SQL Chat API server...")
    print("Environment variables:")
    print(f"  AUTH_TOKEN: {'SET' if os.getenv('AUTH_TOKEN') else 'NOT SET'}")
    print(f"  LLM_MODEL_PROVIDER: {os.getenv('LLM_MODEL_PROVIDER')}")
    print(f"  LLM_MODEL_VERSION: {os.getenv('LLM_MODEL_VERSION')}")
    print("\nServer will be available at: http://localhost:8000")
    print("API documentation at: http://localhost:8000/docs")
    print("\nPress Ctrl+C to stop the server")
    
    # Run the server
    uvicorn.run(
        "nl2sql.api:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )

if __name__ == "__main__":
    main()
