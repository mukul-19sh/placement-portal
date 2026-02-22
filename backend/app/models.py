from sqlalchemy import Column, Integer, String, Float, Boolean
from .database import Base


# ---------- Placement data (unchanged) ----------
class Student(Base):
    """Student profiles for placement matching (name, skills, cgpa)."""
    __tablename__ = "students"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    skills = Column(String, nullable=False)
    cgpa = Column(Float, nullable=False)


class Job(Base):
    __tablename__ = "jobs"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    requirements = Column(String, nullable=False)
    min_cgpa = Column(Float, default=0.0)
    top_n = Column(Integer, default=10)
    created_by = Column(String, nullable=True)


# ---------- Separate auth tables per role ----------
class AdminUser(Base):
    """Administrator credentials (college placement cell)."""
    __tablename__ = "admin_users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)


class CompanyUser(Base):
    """Company/recruiter credentials."""
    __tablename__ = "company_users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)


class StudentUser(Base):
    """Student credentials (job seekers)."""
    __tablename__ = "student_users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)