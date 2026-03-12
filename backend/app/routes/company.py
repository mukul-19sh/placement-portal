from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from ..deps import company_required, get_db
from ..models import Job, Student, StudentUser, ProfileView, Notification, CompanyProfile, JobApplication, Interview, Offer
from ..schemas import CompanyProfileCreate, CompanyProfileResponse
from ..matching import score_student_for_job
from ..utils.email import send_email

router = APIRouter(prefix="/company", tags=["Company"])


# ---------- Pydantic request bodies ----------

class ApplicationStatusUpdate(BaseModel):
    status: str  # under_review | shortlisted | rejected


class InterviewSchedule(BaseModel):
    interview_date: str   # "YYYY-MM-DD"
    interview_time: str   # "HH:MM"
    mode: str             # "Google Meet" | "In-Person" | "Zoom" etc.
    link: Optional[str] = None
    notes: Optional[str] = None


class OfferCreate(BaseModel):
    position: str
    ctc: str              # "10 LPA"


# ---------- Helpers ----------

def _get_company_name(db: Session, email: str) -> str:
    profile = db.query(CompanyProfile).filter(CompanyProfile.owner_email == email).first()
    return profile.company_name if profile else email


def _notify_student(db: Session, student_email: str, message: str):
    db.add(Notification(student_email=student_email, message=message))


# ---------- Dashboard & Profile ----------

@router.get("/dashboard")
def company_dashboard(company=Depends(company_required), db: Session = Depends(get_db)):
    profile = db.query(CompanyProfile).filter(CompanyProfile.owner_email == company.email).first()
    company_name = profile.company_name if profile else "Company"

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


@router.get("/profile", response_model=CompanyProfileResponse)
def get_company_profile(company=Depends(company_required), db: Session = Depends(get_db)):
    profile = db.query(CompanyProfile).filter(CompanyProfile.owner_email == company.email).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile


@router.post("/profile", response_model=CompanyProfileResponse)
def create_or_update_company_profile(
    profile_data: CompanyProfileCreate,
    company=Depends(company_required),
    db: Session = Depends(get_db)
):
    profile = db.query(CompanyProfile).filter(CompanyProfile.owner_email == company.email).first()
    if profile:
        profile.company_name = profile_data.company_name
        profile.manager_name = profile_data.manager_name
        profile.designation = profile_data.designation
    else:
        profile = CompanyProfile(
            owner_email=company.email,
            company_name=profile_data.company_name,
            manager_name=profile_data.manager_name,
            designation=profile_data.designation
        )
        db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


# ---------- Applicant Management ----------

@router.get("/applicants/{job_id}")
def get_job_applicants(
    job_id: int,
    company=Depends(company_required),
    db: Session = Depends(get_db)
):
    """List all applicants for a job posted by this company."""
    job = db.query(Job).filter(Job.id == job_id, Job.created_by == company.email).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found or not owned by you")

    applications = db.query(JobApplication).filter(JobApplication.job_id == job_id).all()

    result = []
    for app in applications:
        student = db.query(Student).filter(Student.owner_email == app.student_email).first()
        if not student:
            continue

        # Fetch interview info if any
        interview = db.query(Interview).filter(Interview.application_id == app.id).first()
        interview_info = None
        if interview:
            interview_info = {
                "date": interview.interview_date,
                "time": interview.interview_time,
                "mode": interview.mode,
                "link": interview.link,
                "notes": interview.notes,
            }

        # Fetch offer info if any
        offer = db.query(Offer).filter(Offer.application_id == app.id).first()
        offer_info = None
        if offer:
            offer_info = {
                "id": offer.id,
                "position": offer.position,
                "ctc": offer.ctc,
                "status": offer.status,
            }

        result.append({
            "application_id": app.id,
            "student_email": app.student_email,
            "student_name": student.name,
            "student_skills": student.skills,
            "student_cgpa": student.cgpa,
            "resume_url": student.resume_url,
            "match_percentage": app.match_percentage,
            "status": app.status,
            "applied_at": app.applied_at.isoformat(),
            "interview": interview_info,
            "offer": offer_info,
        })

    result.sort(key=lambda x: x["match_percentage"], reverse=True)

    return {
        "job_id": job.id,
        "job_title": job.title,
        "total_applicants": len(result),
        "applicants": result,
    }


@router.post("/application/{app_id}/status")
def update_application_status(
    app_id: int,
    body: ApplicationStatusUpdate,
    background_tasks: BackgroundTasks,
    company=Depends(company_required),
    db: Session = Depends(get_db)
):
    """Update application status: under_review | shortlisted | rejected."""
    allowed = {"under_review", "shortlisted", "rejected"}
    if body.status not in allowed:
        raise HTTPException(status_code=400, detail=f"Status must be one of: {allowed}")

    app = db.query(JobApplication).filter(JobApplication.id == app_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    job = db.query(Job).filter(Job.id == app.job_id, Job.created_by == company.email).first()
    if not job:
        raise HTTPException(status_code=403, detail="You do not own this job")

    app.status = body.status
    company_name = _get_company_name(db, company.email)

    status_labels = {
        "under_review": "is now Under Review",
        "shortlisted": "has been Shortlisted ⭐",
        "rejected": "has been Rejected",
    }
    message = f"Your application for {job.title} at {company_name} {status_labels[body.status]}"
    _notify_student(db, app.student_email, message)

    if body.status == "shortlisted":
        student = db.query(Student).filter(Student.owner_email == app.student_email).first()
        if student:
            html = f"""
            <h2>🎉 You've been Shortlisted!</h2>
            <p>Dear {student.name},</p>
            <p>Congratulations! You have been shortlisted for <strong>{job.title}</strong> at <strong>{company_name}</strong>.</p>
            <p>Your match score: {app.match_percentage}%</p>
            <p>Please log in to the placement portal to see further updates.</p>
            """
            background_tasks.add_task(send_email, app.student_email, f"Shortlisted for {job.title}", html)

    db.commit()
    return {"message": f"Application status updated to '{body.status}'", "application_id": app_id}


@router.post("/application/{app_id}/schedule-interview")
def schedule_interview(
    app_id: int,
    body: InterviewSchedule,
    background_tasks: BackgroundTasks,
    company=Depends(company_required),
    db: Session = Depends(get_db)
):
    """Schedule an interview for an applicant."""
    app = db.query(JobApplication).filter(JobApplication.id == app_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    job = db.query(Job).filter(Job.id == app.job_id, Job.created_by == company.email).first()
    if not job:
        raise HTTPException(status_code=403, detail="You do not own this job")

    # Remove existing interview if rescheduling
    existing = db.query(Interview).filter(Interview.application_id == app_id).first()
    if existing:
        db.delete(existing)

    interview = Interview(
        application_id=app_id,
        job_id=app.job_id,
        student_email=app.student_email,
        company_email=company.email,
        interview_date=body.interview_date,
        interview_time=body.interview_time,
        mode=body.mode,
        link=body.link,
        notes=body.notes,
    )
    db.add(interview)
    app.status = "interview"

    company_name = _get_company_name(db, company.email)
    message = (
        f"📅 Interview Scheduled for {job.title} at {company_name} | "
        f"Date: {body.interview_date} | Time: {body.interview_time} | Mode: {body.mode}"
    )
    _notify_student(db, app.student_email, message)

    student = db.query(Student).filter(Student.owner_email == app.student_email).first()
    if student:
        link_line = f'<p><strong>Link:</strong> <a href="{body.link}">{body.link}</a></p>' if body.link else ""
        notes_line = f"<p><strong>Notes:</strong> {body.notes}</p>" if body.notes else ""
        html = f"""
        <h2>📅 Interview Scheduled</h2>
        <p>Dear {student.name},</p>
        <p>An interview has been scheduled for your application to <strong>{job.title}</strong> at <strong>{company_name}</strong>.</p>
        <table style="border-collapse:collapse;">
          <tr><td style="padding:4px 12px;"><strong>Date</strong></td><td>{body.interview_date}</td></tr>
          <tr><td style="padding:4px 12px;"><strong>Time</strong></td><td>{body.interview_time}</td></tr>
          <tr><td style="padding:4px 12px;"><strong>Mode</strong></td><td>{body.mode}</td></tr>
        </table>
        {link_line}
        {notes_line}
        <p>Best of luck!</p>
        """
        background_tasks.add_task(send_email, app.student_email, f"Interview Scheduled – {job.title}", html)

    db.commit()
    return {"message": "Interview scheduled successfully", "application_id": app_id}


@router.post("/application/{app_id}/send-offer")
def send_offer(
    app_id: int,
    body: OfferCreate,
    background_tasks: BackgroundTasks,
    company=Depends(company_required),
    db: Session = Depends(get_db)
):
    """Send a job offer to an applicant."""
    app = db.query(JobApplication).filter(JobApplication.id == app_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    job = db.query(Job).filter(Job.id == app.job_id, Job.created_by == company.email).first()
    if not job:
        raise HTTPException(status_code=403, detail="You do not own this job")

    # Remove existing offer if resending
    existing = db.query(Offer).filter(Offer.application_id == app_id).first()
    if existing:
        db.delete(existing)

    offer = Offer(
        application_id=app_id,
        job_id=app.job_id,
        student_email=app.student_email,
        company_email=company.email,
        position=body.position,
        ctc=body.ctc,
    )
    db.add(offer)
    app.status = "offer"

    company_name = _get_company_name(db, company.email)
    message = f"🎉 Offer Received from {company_name} for {body.position} – CTC: {body.ctc}"
    _notify_student(db, app.student_email, message)

    student = db.query(Student).filter(Student.owner_email == app.student_email).first()
    if student:
        html = f"""
        <h2>🎉 Congratulations! You have received a Job Offer</h2>
        <p>Dear {student.name},</p>
        <p><strong>{company_name}</strong> has extended an offer to you:</p>
        <table style="border-collapse:collapse;">
          <tr><td style="padding:4px 12px;"><strong>Position</strong></td><td>{body.position}</td></tr>
          <tr><td style="padding:4px 12px;"><strong>CTC</strong></td><td>{body.ctc}</td></tr>
        </table>
        <p>Please log in to the placement portal to Accept or Reject this offer.</p>
        """
        background_tasks.add_task(send_email, app.student_email, f"Job Offer – {body.position} at {company_name}", html)

    db.commit()
    return {"message": "Offer sent successfully", "application_id": app_id}


# ---------- Legacy shortlist endpoint ----------

@router.get("/shortlist/{job_id}")
def company_shortlist(
    job_id: int,
    background_tasks: BackgroundTasks,
    company=Depends(company_required),
    db: Session = Depends(get_db),
):
    job = db.query(Job).filter(Job.id == job_id, Job.created_by == company.email).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found or not owned by you")

    students = db.query(Student).all()
    results = []
    shortlisted_students = []

    for s in students:
        scoring = score_student_for_job(s, job)
        student_data = {
            "student_id": s.id,
            "name": s.name,
            "skills": s.skills,
            "cgpa": s.cgpa,
            "resume_url": s.resume_url,
            "score": scoring if isinstance(scoring, (int, float)) else scoring.get("score", scoring),
        }
        results.append(student_data)
        if isinstance(scoring, dict) and scoring.get("overall_match_percentage", 0) >= 70:
            shortlisted_students.append(s)

    ranked = sorted(results, key=lambda x: x["score"], reverse=True)

    for student in shortlisted_students:
        if student.owner_email:
            notification = Notification(
                student_email=student.owner_email,
                message=f"You were shortlisted for {job.title}!"
            )
            db.add(notification)
            html = f"""
            <h2>Congratulations! You've been shortlisted</h2>
            <p>Dear {student.name}, you were shortlisted for <strong>{job.title}</strong>.</p>
            """
            background_tasks.add_task(send_email, student.owner_email, f"Shortlisted for {job.title}", html)

    db.commit()
    return {
        "job": job.title,
        "results": ranked,
        "shortlisted_count": len(shortlisted_students),
        "total_students": len(students)
    }


@router.post("/profile/view/{student_id}")
def log_company_profile_view(
    student_id: int,
    company=Depends(company_required),
    db: Session = Depends(get_db)
):
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    db.add(ProfileView(student_id=student_id, viewer_email=company.email, viewer_role="company"))
    db.add(Notification(student_email=student.owner_email, message=f"Your profile was viewed by {company.email} (Company)"))
    db.commit()
    return {"message": "Profile view logged"}


@router.get("/student/{student_id}")
def get_student_profile(
    student_id: int,
    company=Depends(company_required),
    db: Session = Depends(get_db)
):
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    db.add(ProfileView(student_id=student_id, viewer_email=company.email, viewer_role="company"))
    db.add(Notification(student_email=student.owner_email, message=f"Your profile was viewed by {company.email} (Company)"))
    db.commit()
    return {
        "id": student.id,
        "name": student.name,
        "skills": student.skills,
        "cgpa": student.cgpa,
        "resume_url": student.resume_url,
        "has_resume": bool(student.resume_url)
    }
