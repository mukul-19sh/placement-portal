from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text
from datetime import datetime
from .database import Base


class Student(Base):
    """Student profiles for placement matching (name, skills, cgpa)."""
    __tablename__ = "students"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    skills = Column(String, nullable=False)
    cgpa = Column(Float, nullable=False)
    resume_url = Column(String, nullable=True)
    owner_email = Column(String, nullable=True, index=True)


class Job(Base):
    __tablename__ = "jobs"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    requirements = Column(String, nullable=False)
    min_cgpa = Column(Float, default=0.0)
    top_n = Column(Integer, default=10)
    created_by = Column(String, nullable=True)


class CompanyProfile(Base):
    """Company profile details."""
    __tablename__ = "company_profiles"
    id = Column(Integer, primary_key=True, index=True)
    owner_email = Column(String, unique=True, index=True, nullable=False)
    company_name = Column(String, nullable=False)
    manager_name = Column(String, nullable=False)
    designation = Column(String, nullable=False)


# ---------- Separate auth tables per role ----------
class AdminUser(Base):
    """Administrator credentials (college placement cell)."""
    __tablename__ = "admin_users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)


class CompanyUser(Base):
    """Company/recruiter credentials."""
    __tablename__ = "company_users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)


class StudentUser(Base):
    """Student credentials (job seekers)."""
    __tablename__ = "student_users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)


class EmailVerificationToken(Base):
    __tablename__ = "email_verification_tokens"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, index=True, nullable=False)
    role = Column(String, nullable=False)
    token = Column(String, unique=True, nullable=False, index=True)
    expires_at = Column(DateTime, nullable=False)
    used = Column(Boolean, default=False)


class ProfileView(Base):
    __tablename__ = "profile_views"
    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, index=True, nullable=False)
    viewer_email = Column(String, nullable=False)
    viewer_role = Column(String, nullable=False)
    viewed_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class Notification(Base):
    __tablename__ = "notifications"
    id = Column(Integer, primary_key=True, index=True)
    student_email = Column(String, index=True, nullable=False)
    message = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    is_read = Column(Boolean, default=False)


class JobApplication(Base):
    """
    Statuses: applied | under_review | shortlisted | interview | rejected | offer
    """
    __tablename__ = "job_applications"
    id = Column(Integer, primary_key=True, index=True)
    student_email = Column(String, index=True, nullable=False)
    job_id = Column(Integer, index=True, nullable=False)
    applied_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    status = Column(String, default="applied")
    match_percentage = Column(Float, nullable=False)


class Interview(Base):
    """Interview details scheduled by a company for a job application."""
    __tablename__ = "interviews"
    id = Column(Integer, primary_key=True, index=True)
    application_id = Column(Integer, index=True, nullable=False)
    job_id = Column(Integer, index=True, nullable=False)
    student_email = Column(String, index=True, nullable=False)
    company_email = Column(String, nullable=False)
    interview_date = Column(String, nullable=False)   # "YYYY-MM-DD"
    interview_time = Column(String, nullable=False)   # "HH:MM"
    mode = Column(String, nullable=False)             # "Google Meet", "In-Person", etc.
    link = Column(String, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class Offer(Base):
    """Job offer sent by a company to a student."""
    __tablename__ = "offers"
    id = Column(Integer, primary_key=True, index=True)
    application_id = Column(Integer, index=True, nullable=False)
    job_id = Column(Integer, index=True, nullable=False)
    student_email = Column(String, index=True, nullable=False)
    company_email = Column(String, nullable=False)
    position = Column(String, nullable=False)
    ctc = Column(String, nullable=False)              # e.g. "10 LPA"
    status = Column(String, default="pending")        # pending | accepted | rejected
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class AdminNotification(Base):
    __tablename__ = "admin_notifications"
    id = Column(Integer, primary_key=True, index=True)
    admin_email = Column(String, index=True, nullable=True)  # None = all admins
    message = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    is_read = Column(Boolean, default=False)
