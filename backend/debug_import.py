import traceback
import sys
import os

# Add current directory to path
sys.path.insert(0, os.getcwd())

print(f"Current working directory: {os.getcwd()}")
print(f"Python path: {sys.path}")

try:
    print("Attempting to import app.main...")
    from app.main import app
    print("SUCCESS: app.main imported correctly")
except ImportError as e:
    print(f"IMPORT ERROR: {e}")
    traceback.print_exc()
except Exception as e:
    print(f"GENERAL ERROR: {e}")
    traceback.print_exc()
