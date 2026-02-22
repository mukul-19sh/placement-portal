from pydantic import BaseModel, EmailStr
from typing import List, Optional

# ---------- Students ----------
class StudentCreate(BaseModel):
    name: str
    skills: str
    cgpa: float

class StudentBulkCreate(BaseModel):
    students: List[StudentCreate]

# ---------- Jobs ----------
class JobCreate(BaseModel):
    title: str
    requirements: str
    min_cgpa: float
    top_n: int

# ---------- Auth / Users ----------
class UserCreate(BaseModel):
    email: EmailStr
    password: str
    role: str

class Token(BaseModel):
    access_token: str
    token_type: str
