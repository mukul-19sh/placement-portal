import time
import os
from typing import Dict, Optional
from fastapi import HTTPException, Request
from functools import wraps
import hashlib
import secrets

# Rate limiting storage (in production, use Redis)
rate_limit_store: Dict[str, Dict] = {}

# Security configuration
MAX_LOGIN_ATTEMPTS = int(os.getenv("MAX_LOGIN_ATTEMPTS", "5"))
LOGIN_COOLDOWN_MINUTES = int(os.getenv("LOGIN_COOLDOWN_MINUTES", "15"))
RATE_LIMIT_REQUESTS = int(os.getenv("RATE_LIMIT_REQUESTS", "100"))
RATE_LIMIT_WINDOW = int(os.getenv("RATE_LIMIT_WINDOW", "3600"))  # 1 hour

# Profile view rate limiting
PROFILE_VIEW_LIMIT = int(os.getenv("PROFILE_VIEW_LIMIT", "50"))
PROFILE_VIEW_WINDOW = int(os.getenv("PROFILE_VIEW_WINDOW", "86400"))  # 24 hours


class RateLimiter:
    """Simple in-memory rate limiter."""
    
    @staticmethod
    def is_allowed(
        key: str, 
        max_requests: int, 
        window_seconds: int
    ) -> bool:
        """Check if request is allowed based on rate limit."""
        now = time.time()
        
        if key not in rate_limit_store:
            rate_limit_store[key] = {
                "requests": [],
                "count": 0
            }
        
        # Clean old requests
        cutoff = now - window_seconds
        rate_limit_store[key]["requests"] = [
            req_time for req_time in rate_limit_store[key]["requests"]
            if req_time > cutoff
        ]
        
        # Check if under limit
        if len(rate_limit_store[key]["requests"]) < max_requests:
            rate_limit_store[key]["requests"].append(now)
            return True
        
        return False
    
    @staticmethod
    def get_remaining_requests(
        key: str, 
        max_requests: int, 
        window_seconds: int
    ) -> int:
        """Get remaining requests for rate limit."""
        now = time.time()
        
        if key not in rate_limit_store:
            return max_requests
        
        # Clean old requests
        cutoff = now - window_seconds
        rate_limit_store[key]["requests"] = [
            req_time for req_time in rate_limit_store[key]["requests"]
            if req_time > cutoff
        ]
        
        return max_requests - len(rate_limit_store[key]["requests"])


class LoginAttemptTracker:
    """Track login attempts for security."""
    
    @staticmethod
    def get_key(email: str) -> str:
        """Generate key for login attempts."""
        return f"login_attempts:{hashlib.md5(email.lower().encode()).hexdigest()}"
    
    @staticmethod
    def is_locked(email: str) -> tuple[bool, Optional[int]]:
        """Check if account is locked due to failed attempts."""
        key = LoginAttemptTracker.get_key(email)
        
        if key not in rate_limit_store:
            return False, None
        
        attempts_data = rate_limit_store[key]
        
        # Check if locked
        if attempts_data.get("locked_until"):
            if time.time() < attempts_data["locked_until"]:
                return True, int(attempts_data["locked_until"] - time.time())
            else:
                # Lock expired, reset
                del rate_limit_store[key]
                return False, None
        
        return False, None
    
    @staticmethod
    def record_failed_attempt(email: str):
        """Record a failed login attempt."""
        key = LoginAttemptTracker.get_key(email)
        
        if key not in rate_limit_store:
            rate_limit_store[key] = {"failed_attempts": 0}
        
        rate_limit_store[key]["failed_attempts"] += 1
        
        # Lock account if too many attempts
        if rate_limit_store[key]["failed_attempts"] >= MAX_LOGIN_ATTEMPTS:
            rate_limit_store[key]["locked_until"] = time.time() + (LOGIN_COOLDOWN_MINUTES * 60)
    
    @staticmethod
    def record_successful_attempt(email: str):
        """Record a successful login (reset failed attempts)."""
        key = LoginAttemptTracker.get_key(email)
        
        if key in rate_limit_store:
            del rate_limit_store[key]


class SecurityUtils:
    """Security utility functions."""
    
    @staticmethod
    def generate_secure_token(length: int = 32) -> str:
        """Generate a secure random token."""
        return secrets.token_urlsafe(length)
    
    @staticmethod
    def hash_sensitive_data(data: str) -> str:
        """Hash sensitive data for logging/analytics."""
        return hashlib.sha256(data.encode()).hexdigest()[:16]
    
    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """Sanitize filename for security."""
        # Remove path components
        filename = os.path.basename(filename)
        
        # Remove dangerous characters
        dangerous_chars = ['..', '/', '\\', ':', '*', '?', '"', '<', '>', '|']
        for char in dangerous_chars:
            filename = filename.replace(char, '_')
        
        # Limit length
        if len(filename) > 255:
            name, ext = os.path.splitext(filename)
            filename = name[:255-len(ext)] + ext
        
        return filename
    
    @staticmethod
    def validate_file_content(content: bytes, expected_type: str = None) -> bool:
        """Validate file content to prevent malicious uploads."""
        # Check file size (max 10MB)
        if len(content) > 10 * 1024 * 1024:
            return False
        
        # Basic content validation
        if expected_type == "pdf":
            # Check PDF signature
            return content.startswith(b'%PDF')
        elif expected_type == "image":
            # Check common image signatures
            image_signatures = [
                b'\xFF\xD8\xFF',  # JPEG
                b'\x89PNG\r\n\x1a\n',  # PNG
                b'GIF87a',  # GIF
                b'GIF89a',  # GIF
            ]
            return any(content.startswith(sig) for sig in image_signatures)
        
        return True


def rate_limit(max_requests: int, window_seconds: int, key_func=None):
    """Rate limiting decorator."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Get request from kwargs or args
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            
            if not request:
                # Try to get from kwargs
                for key, value in kwargs.items():
                    if isinstance(value, Request):
                        request = value
                        break
            
            if request:
                # Generate rate limit key
                if key_func:
                    rate_key = key_func(request)
                else:
                    rate_key = f"rate_limit:{request.client.host}:{func.__name__}"
                
                if not RateLimiter.is_allowed(rate_key, max_requests, window_seconds):
                    remaining = RateLimiter.get_remaining_requests(rate_key, max_requests, window_seconds)
                    raise HTTPException(
                        status_code=429,
                        detail={
                            "error": "Rate limit exceeded",
                            "remaining_requests": remaining,
                            "reset_time": window_seconds
                        }
                    )
            
            return func(*args, **kwargs)
        return wrapper
    return decorator


def profile_view_rate_limit(func):
    """Specific rate limiter for profile views."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Extract student email from function arguments
        student_email = None
        for arg in args:
            if hasattr(arg, 'email'):
                student_email = arg.email
                break
        
        if student_email:
            rate_key = f"profile_views:{student_email}"
            
            if not RateLimiter.is_allowed(rate_key, PROFILE_VIEW_LIMIT, PROFILE_VIEW_WINDOW):
                raise HTTPException(
                    status_code=429,
                    detail="Profile view rate limit exceeded. Please try again later."
                )
        
        return func(*args, **kwargs)
    return wrapper


def login_security_check(func):
    """Security check for login attempts."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Extract email from form data
        email = None
        for arg in args:
            if hasattr(arg, 'username'):  # OAuth2PasswordRequestForm
                email = arg.username
                break
        
        if email:
            # Check if account is locked
            is_locked, remaining_time = LoginAttemptTracker.is_locked(email)
            
            if is_locked:
                raise HTTPException(
                    status_code=423,
                    detail=f"Account temporarily locked. Try again in {remaining_time // 60} minutes."
                )
        
        try:
            return func(*args, **kwargs)
        except HTTPException as e:
            # If login failed, record attempt
            if email and e.status_code == 401:
                LoginAttemptTracker.record_failed_attempt(email)
            raise
        except Exception as e:
            # If login succeeded, clear failed attempts
            if email:
                LoginAttemptTracker.record_successful_attempt(email)
            raise
    
    return wrapper


# Security headers middleware
def add_security_headers(response):
    """Add security headers to response."""
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Content-Security-Policy"] = "default-src 'self'"
    
    return response
