#!/usr/bin/env python3
"""
Research Paper Summarization System - Refactored Main Application
Clean entry point for the research paper analysis and summarization system.
"""

import uvicorn
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.api.app import app
from src.config.settings import settings


def main():
    """Main application entry point"""
    print("🚀 Starting Research Paper Summarization API...")
    print("=" * 60)
    print("Available endpoints:")
    print("- GET / - Health check")
    print("- GET /app - Web Interface")
    print("- POST /api/v1/process/search - Search and process papers")
    print("- POST /api/v1/process/upload - Upload and process PDFs")
    print("- GET /api/v1/status/{workflow_id} - Get workflow status")
    print("- WebSocket /ws/status/{workflow_id} - Real-time updates")
    print("\n🌐 Access the application:")
    print(f"   Web Interface: http://{settings.api_host}:{settings.api_port}/app")
    print(f"   API Docs: http://{settings.api_host}:{settings.api_port}/docs")
    print(f"   Health Check: http://{settings.api_host}:{settings.api_port}")
    print("=" * 60)
    print("Press Ctrl+C to stop the server")
    print()
    
    try:
        uvicorn.run(
            app, 
            host=settings.api_host,
            port=settings.api_port,
            reload=settings.api_reload,
            log_level="info"
        )
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")
    except Exception as e:
        print(f"❌ Error starting server: {e}")
        print("\n💡 Try running with uvicorn directly:")
        print(f"   uvicorn main:app --host {settings.api_host} --port {settings.api_port} --reload")


if __name__ == "__main__":
    main()
