from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..deps import student_required, get_db
from ..models import Job

router = APIRouter(prefix="/student", tags=["Student"])


@router.get("/dashboard")
def student_dashboard(
    student=Depends(student_required),
    db: Session = Depends(get_db),
):
    """Student dashboard with stats and welcome message."""
    total_jobs = db.query(Job).count()
    return {
        "message": "Welcome to Student Dashboard!",
        "user_email": student.email,
        "stats": {
            "available_jobs": total_jobs,
        },
    }
