from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..deps import admin_required, get_db
from ..models import Student, Job
from ..matching import score_student_for_job

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/dashboard")
def admin_dashboard(admin=Depends(admin_required), db: Session = Depends(get_db)):
    """Admin dashboard with stats."""
    total_students = db.query(Student).count()
    total_jobs = db.query(Job).count()
    return {
        "message": "Welcome to Admin Dashboard!",
        "user_email": admin.email,
        "stats": {
            "total_students": total_students,
            "total_jobs": total_jobs,
        },
    }

@router.get("/shortlist/{job_id}")
def shortlist_students(job_id: int, db: Session = Depends(get_db), admin=Depends(admin_required)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    students = db.query(Student).all()

    results = []
    for s in students:
        scoring = score_student_for_job(s, job)
        results.append({
            "student_id": s.id,
            "name": s.name,
            "skills": s.skills,
            "cgpa": s.cgpa,
            "score": scoring if isinstance(scoring, (int, float)) else scoring.get("score", scoring),
        })

    ranked = sorted(results, key=lambda x: x["score"], reverse=True)

    return {
        "job": job.title,
        "results": ranked
    }

