from fastapi import APIRouter, BackgroundTasks, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional

from ..database import SessionLocal
from ..models import Job, StudentUser
from ..schemas import JobCreate
from ..deps import get_current_user
from ..utils.email import send_email

router = APIRouter(prefix="/jobs", tags=["Jobs"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/")
def add_job(
    job: JobCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    new_job = Job(**job.dict(), created_by=user.email)
    db.add(new_job)
    db.commit()
    db.refresh(new_job)

    # Notify all student users about new job (non-blocking)
    students = db.query(StudentUser).all()
    if students:
        subject = f"New job posted: {new_job.title}"
        html = f"""
        <h2>New Job Posted</h2>
        <p><strong>Title:</strong> {new_job.title}</p>
        <p><strong>Posted by:</strong> {user.email}</p>
        <p><strong>Min CGPA:</strong> {new_job.min_cgpa}</p>
        <p><strong>Required Skills:</strong> {new_job.requirements}</p>
        """
        for s in students:
            background_tasks.add_task(send_email, s.email, subject, html)

    return new_job


@router.get("/")
def get_jobs(
    owner: Optional[str] = Query(None, description="Filter by creator email"),
    db: Session = Depends(get_db),
):
    query = db.query(Job)
    if owner:
        query = query.filter(Job.created_by == owner)
    return query.all()
