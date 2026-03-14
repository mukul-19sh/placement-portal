from pydantic import BaseModel, EmailStr
from typing import List, Optional

# ---------- Students ----------
class StudentCreate(BaseModel):
    name: str
    skills: str
    cgpa: float


class StudentProfile(BaseModel):
    full_name: str
    skills: str
    cgpa: float
    linkedin_url: Optional[str] = None
    github_url: Optional[str] = None

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

# ---------- Company ----------
class CompanyProfileBase(BaseModel):
    company_name: str
    manager_name: str
    designation: str

class CompanyProfileCreate(CompanyProfileBase):
    pass

class CompanyProfileResponse(CompanyProfileBase):
    id: int
    owner_email: EmailStr

    class Config:
        orm_mode = True
