#!/usr/bin/env python3
"""
Startup script for Placement Portal Backend
"""
import sys
import os

# Add the current directory to Python path so it can find the app module
backend_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, backend_dir)

# Change current working directory to backend so that uvicorn subprocesses find 'app'
os.chdir(backend_dir)

try:
    import uvicorn
    
    if __name__ == "__main__":
        print("🚀 Starting Placement Portal Backend...")
        print("📍 URL: http://localhost:8000")
        print("📍 Health Check: http://localhost:8000/health")
        print("Press Ctrl+C to stop")
        print("-" * 50)
        
        uvicorn.run(
            "app.main:app",
            host="127.0.0.1",
            port=8000,
            reload=True,
            log_level="info"
        )
except Exception as e:
    print(f"❌ ERROR: {e}")
    print("-" * 50)
    print("Make sure all dependencies are installed:")
    print("   pip install -r requirements.txt")
    print("-" * 50)
    input("Press Enter to close...")
    sys.exit(1)
