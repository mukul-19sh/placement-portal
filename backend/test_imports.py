#!/usr/bin/env python3
"""
Test script to check if all imports work correctly
"""

try:
    import app.main
    print("✅ app.main imported successfully")
except ImportError as e:
    print(f"❌ Failed to import app.main: {e}")

try:
    from app.utils.database_cleanup import run_full_cleanup
    print("✅ database_cleanup imported successfully")
except ImportError as e:
    print(f"❌ Failed to import database_cleanup: {e}")

try:
    from app.routes.admin import router as admin_router
    print("✅ admin routes imported successfully")
except ImportError as e:
    print(f"❌ Failed to import admin routes: {e}")

print("\n🚀 If all imports are successful, the application should run without issues!")
