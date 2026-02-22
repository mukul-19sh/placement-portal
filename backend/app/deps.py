from fastapi import Depends, HTTPException, status
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordBearer

from .database import SessionLocal
from .models import AdminUser, CompanyUser, StudentUser
from .auth import SECRET_KEY, ALGORITHM

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

ROLE_MODELS = {
    "admin": AdminUser,
    "company": CompanyUser,
    "student": StudentUser,
}


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str | None = payload.get("sub")
        role: str | None = payload.get("role")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    # Look up user in the correct table based on role in token
    if role and role in ROLE_MODELS:
        model = ROLE_MODELS[role]
        user = db.query(model).filter(model.email == email).first()
    else:
        # Fallback: try all tables
        user = None
        for model in ROLE_MODELS.values():
            user = db.query(model).filter(model.email == email).first()
            if user:
                role = "admin" if model == AdminUser else "company" if model == CompanyUser else "student"
                break

    if user is None:
        raise credentials_exception

    # Return object with email and role for route protection
    class AuthUser:
        def __init__(self, email: str, role: str):
            self.email = email
            self.role = role

    return AuthUser(email=email, role=role or "student")


def admin_required(current_user=Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


def company_required(current_user=Depends(get_current_user)):
    if current_user.role != "company":
        raise HTTPException(status_code=403, detail="Company access required")
    return current_user


def student_required(current_user=Depends(get_current_user)):
    if current_user.role != "student":
        raise HTTPException(status_code=403, detail="Student access required")
    return current_user
