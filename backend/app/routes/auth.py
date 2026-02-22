from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

from ..database import SessionLocal
from ..models import AdminUser, CompanyUser, StudentUser
from ..schemas import UserCreate, Token
from ..auth import get_password_hash, verify_password, create_access_token

router = APIRouter(prefix="/auth", tags=["Auth"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

# Map role to model and table
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


@router.post("/register")
def register(user: UserCreate, db: Session = Depends(get_db)):
    role = user.role.lower()
    if role not in ROLE_MODELS:
        raise HTTPException(status_code=400, detail="Invalid role. Use: admin, company, or student")

    existing = _get_user_by_email(db, user.email, role)
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered for this role")

    _create_user(db, user.email, get_password_hash(user.password), role)
    return {"message": "User registered successfully"}


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
        return {"access_token": create_access_token({"sub": email, "role": role.lower()}), "token_type": "bearer"}

    # No role: try all tables
    for r, _ in ROLE_MODELS.items():
        user = _get_user_by_email(db, email, r)
        if user and verify_password(password, user.hashed_password):
            return {"access_token": create_access_token({"sub": email, "role": r}), "token_type": "bearer"}

    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
