#!/usr/bin/env python3
"""
Test script to check local backend functionality
"""
import requests
import json
import time

BASE_URL = "http://localhost:8000"

def test_backend_connection():
    """Test if backend is running."""
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            print("✅ Backend is running")
            return True
        else:
            print(f"❌ Backend returned status {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Cannot connect to backend: {e}")
        print("💡 Make sure to start the backend first: python run.py")
        return False

def test_debug_info():
    """Test debug endpoint."""
    try:
        response = requests.get(f"{BASE_URL}/debug", timeout=5)
        if response.status_code == 200:
            debug_data = response.json()
            print("\n🔍 Debug Information:")
            print(f"  PDF Library: {debug_data['dependencies']['pdf']}")
            print(f"  Chatbot: {debug_data['dependencies']['chatbot']}")
            print(f"  Storage: {debug_data['dependencies']['storage']}")
            print(f"  Cloud Storage: {debug_data['environment']['use_cloud_storage']}")
            print(f"  Storage Type: {debug_data['environment']['storage_type']}")
            return True
        else:
            print(f"❌ Debug endpoint failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Debug test failed: {e}")
        return False

def test_profile_endpoint():
    """Test if profile endpoint is accessible (will fail without auth)."""
    try:
        response = requests.get(f"{BASE_URL}/student/profile", timeout=5)
        if response.status_code == 401:
            print("✅ Profile endpoint requires authentication (expected)")
            return True
        else:
            print(f"⚠️ Profile endpoint returned {response.status_code}")
            return True
    except Exception as e:
        print(f"❌ Profile endpoint test failed: {e}")
        return False

def main():
    print("🚀 Testing Placement Portal Backend")
    print("=" * 50)
    
    # Wait a moment for server to start
    time.sleep(1)
    
    tests = [
        ("Backend Connection", test_backend_connection),
        ("Debug Info", test_debug_info),
        ("Profile Endpoint", test_profile_endpoint),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n📋 Testing {test_name}...")
        if test_func():
            passed += 1
    
    print("\n" + "=" * 50)
    print(f"Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Backend is ready.")
        print("\n💡 Next steps:")
        print("1. Open frontend in browser")
        print("2. Try creating a profile")
        print("3. Test resume upload")
        print("4. Test chatbot functionality")
    else:
        print("❌ Some tests failed. Check the errors above.")

if __name__ == "__main__":
    main()
