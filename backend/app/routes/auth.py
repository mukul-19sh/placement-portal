from datetime import datetime, timedelta
import secrets

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

from ..database import SessionLocal
from ..models import AdminUser, CompanyUser, StudentUser, EmailVerificationToken
from ..schemas import UserCreate, Token
from ..auth import get_password_hash, verify_password, create_access_token
from ..utils.email import send_email

router = APIRouter(prefix="/auth", tags=["Auth"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

# Map role to model and table
ROLE_MODELS = {
    "admin": AdminUser,
    "company": CompanyUser,
    "student": StudentUser,
}

EMAIL_TOKEN_EXPIRE_MINUTES = 15


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _get_user_by_email(db: Session, email: str, role: str):
    """Get user from the correct table based on role."""
    model = ROLE_MODELS.get(role)
    if not model:
        return None
    return db.query(model).filter(model.email == email).first()


def _create_user(db: Session, email: str, hashed_password: str, role: str):
    """Create user in the correct table based on role."""
    model = ROLE_MODELS.get(role)
    if not model:
        raise HTTPException(status_code=400, detail="Invalid role")
    new_user = model(email=email, hashed_password=hashed_password)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


def _create_verification_token(db: Session, email: str, role: str) -> EmailVerificationToken:
    token = secrets.token_urlsafe(32)
    expires_at = datetime.utcnow() + timedelta(minutes=EMAIL_TOKEN_EXPIRE_MINUTES)
    ev = EmailVerificationToken(email=email, role=role, token=token, expires_at=expires_at, used=False)
    db.add(ev)
    db.commit()
    db.refresh(ev)
    return ev


def _send_verification_email(base_url: str, email: str, role: str, token: str) -> bool:
    verify_link = f"{base_url.rstrip('/')}/auth/verify-email?token={token}"
    subject = "Verify your Placement Portal account"
    html = f"""
    <h2>Verify your email</h2>
    <p>Hello,</p>
    <p>You created a {role} account on the Placement Portal. Please verify your email by clicking the link below:</p>
    <p><a href="{verify_link}">Verify Email</a></p>
    <p>This link will expire in {EMAIL_TOKEN_EXPIRE_MINUTES} minutes.</p>
    """
    return send_email(email, subject, html)


@router.post("/register")
def register(user: UserCreate, request: Request, db: Session = Depends(get_db)):
    role = user.role.lower()
    if role not in ROLE_MODELS:
        raise HTTPException(status_code=400, detail="Invalid role. Use: admin, company, or student")

    existing = _get_user_by_email(db, user.email, role)
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered for this role")

    _create_user(db, user.email, get_password_hash(user.password), role)
    ev = _create_verification_token(db, user.email, role)
    base_url = str(request.base_url)
    email_sent = _send_verification_email(base_url, user.email, role, ev.token)
    
    if email_sent:
        return {"message": "Registration successful. Please check your email to verify your account."}
    else:
        return {
            "message": "Registration successful but email verification failed. Please check your SMTP configuration.",
            "email_sent": False,
            "verification_token": ev.token  # For development only
        }


@router.post("/login", response_model=Token)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
    role: str | None = Query(None, description="Role: admin, company, or student"),
):
    email = form_data.username
    password = form_data.password

    # If role provided, check only that table
    if role and role.lower() in ROLE_MODELS:
        user = _get_user_by_email(db, email, role.lower())
        if not user or not verify_password(password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials",
            )
        if not getattr(user, "is_verified", False):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Email not verified. Please check your inbox.",
            )
        return {"access_token": create_access_token({"sub": email, "role": role.lower()}), "token_type": "bearer"}

    # No role: try all tables
    for r, _ in ROLE_MODELS.items():
        user = _get_user_by_email(db, email, r)
        if user and verify_password(password, user.hashed_password):
            if not getattr(user, "is_verified", False):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Email not verified. Please check your inbox.",
                )
            return {"access_token": create_access_token({"sub": email, "role": r}), "token_type": "bearer"}

    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")


@router.get("/verify-email")
def verify_email(token: str, db: Session = Depends(get_db)):
    ev = db.query(EmailVerificationToken).filter(EmailVerificationToken.token == token).first()
    if not ev or ev.used:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired token")
    if ev.expires_at < datetime.utcnow():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Token has expired")

    user = _get_user_by_email(db, ev.email, ev.role)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.is_verified = True
    ev.used = True
    db.add(user)
    db.add(ev)
    db.commit()

    return {"message": "Email verified successfully. You can now log in."}


@router.post("/resend-verification")
def resend_verification(email: str = Query(...), role: str = Query(...), request: Request = None, db: Session = Depends(get_db)):
    role = role.lower()
    if role not in ROLE_MODELS:
        raise HTTPException(status_code=400, detail="Invalid role")

    user = _get_user_by_email(db, email, role)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if getattr(user, "is_verified", False):
        return {"message": "Email already verified"}

    # Optionally invalidate old tokens; here we just create a new one.
    ev = _create_verification_token(db, email, role)
    base_url = str(request.base_url) if request is not None else ""
    _send_verification_email(base_url, email, role, ev.token)
    return {"message": "Verification email resent. Please check your inbox."}
