import traceback
import sys

try:
    print("Attempting to initialize passlib CryptContext...")
    from passlib.context import CryptContext
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    print("SUCCESS: CryptContext initialized")
except Exception as e:
    print(f"ERROR: {e}")
    traceback.print_exc()
    sys.exit(1)
