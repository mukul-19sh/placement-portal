from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional

from ..database import SessionLocal
from ..models import Job
from ..schemas import JobCreate
from ..deps import get_current_user

router = APIRouter(prefix="/jobs", tags=["Jobs"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/")
def add_job(job: JobCreate, db: Session = Depends(get_db), user=Depends(get_current_user)):
    new_job = Job(**job.dict(), created_by=user.email)
    db.add(new_job)
    db.commit()
    db.refresh(new_job)
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
