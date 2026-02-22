from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..deps import company_required, get_db
from ..models import Job, Student
from ..matching import score_student_for_job

router = APIRouter(prefix="/company", tags=["Company"])


@router.get("/dashboard")
def company_dashboard(company=Depends(company_required), db: Session = Depends(get_db)):
    my_jobs = db.query(Job).filter(Job.created_by == company.email).count()
    total_jobs = db.query(Job).count()
    return {
        "message": "Welcome to Company Dashboard!",
        "user_email": company.email,
        "stats": {
            "my_jobs": my_jobs,
            "total_jobs_posted": total_jobs,
        },
    }


@router.get("/my-jobs")
def get_my_jobs(company=Depends(company_required), db: Session = Depends(get_db)):
    return db.query(Job).filter(Job.created_by == company.email).all()


@router.get("/shortlist/{job_id}")
def company_shortlist(job_id: int, company=Depends(company_required), db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id, Job.created_by == company.email).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found or not owned by you")

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
    return {"job": job.title, "results": ranked}
