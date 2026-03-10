#!/usr/bin/env python3
"""
Quick test to verify backend is working correctly
"""
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

print("=" * 60)
print("PLACEMENT PORTAL - Backend Diagnostic")
print("=" * 60)

# Test 1: Check imports
print("\n[1/5] Testing imports...")
try:
    from app.main import app
    print("✅ App imports successfully")
except Exception as e:
    print(f"❌ Import failed: {e}")
    sys.exit(1)

# Test 2: Check CORS middleware
print("\n[2/5] Checking CORS configuration...")
try:
    from fastapi.testclient import TestClient
    client = TestClient(app)
    
    # Test preflight
    response = client.options("/health", headers={
        "Origin": "http://localhost:3000",
        "Access-Control-Request-Method": "GET"
    })
    
    cors_origin = response.headers.get("access-control-allow-origin")
    if cors_origin == "*":
        print(f"✅ CORS preflight working (Allow-Origin: {cors_origin})")
    else:
        print(f"⚠️ CORS may have issues (Allow-Origin: {cors_origin})")
        
except Exception as e:
    print(f"❌ CORS test failed: {e}")

# Test 3: Test health endpoint
print("\n[3/5] Testing health endpoint...")
try:
    response = client.get("/health")
    if response.status_code == 200:
        print(f"✅ Health endpoint working: {response.json()}")
    else:
        print(f"❌ Health endpoint returned {response.status_code}")
except Exception as e:
    print(f"❌ Health test failed: {e}")

# Test 4: Test auth endpoints exist
print("\n[4/5] Testing auth endpoints...")
try:
    # Test register (will fail with validation error but should not be 404)
    response = client.post("/auth/register", json={})
    if response.status_code in [400, 422]:  # Validation error is expected
        print("✅ Auth register endpoint exists")
    elif response.status_code == 404:
        print("❌ Auth register endpoint not found")
    else:
        print(f"⚠️ Auth register returned {response.status_code}")
        
    # Test login (will fail but should not be 404)
    response = client.post("/auth/login", data={})
    if response.status_code in [400, 401, 422]:  # Expected errors
        print("✅ Auth login endpoint exists")
    elif response.status_code == 404:
        print("❌ Auth login endpoint not found")
    else:
        print(f"⚠️ Auth login returned {response.status_code}")
        
except Exception as e:
    print(f"❌ Auth test failed: {e}")

# Test 5: Check CORS on actual request
print("\n[5/5] Testing CORS on actual request...")
try:
    response = client.get("/health", headers={"Origin": "http://localhost:3000"})
    cors_origin = response.headers.get("access-control-allow-origin")
    if cors_origin:
        print(f"✅ CORS headers present on regular request (Allow-Origin: {cors_origin})")
    else:
        print(f"❌ No CORS headers on regular response!")
        print(f"   Headers: {dict(response.headers)}")
except Exception as e:
    print(f"❌ CORS test failed: {e}")

print("\n" + "=" * 60)
print("DIAGNOSTIC COMPLETE")
print("=" * 60)
print("\nIf all tests passed but you still see 'failed to fetch':")
print("1. Make sure backend is actually running: python run.py")
print("2. Check browser console (F12) for exact error")
print("3. Try accessing http://localhost:8000/health in browser")
print("4. Check Windows Defender/antivirus isn't blocking port 8000")
