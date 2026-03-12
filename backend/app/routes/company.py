from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session

from ..deps import company_required, get_db
from ..models import Job, Student, StudentUser, ProfileView, Notification, CompanyProfile
from ..schemas import CompanyProfileCreate, CompanyProfileResponse
from ..matching import score_student_for_job
from ..utils.email import send_email

router = APIRouter(prefix="/company", tags=["Company"])


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
    """Get the current company's profile."""
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
    """Create or update company profile."""
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
        
        # Consider top 50% as shortlisted
        if isinstance(scoring, dict) and scoring.get("overall_match_percentage", 0) >= 70:
            shortlisted_students.append(s)

    ranked = sorted(results, key=lambda x: x["score"], reverse=True)

    # Enhanced email notification to shortlisted students
    for student in shortlisted_students:
        if student.owner_email:
            # Create notification
            notification = Notification(
                student_email=student.owner_email,
                message=f"You were shortlisted for {job.title} at {company.email}!"
            )
            db.add(notification)
            
            # Send email
            subject = f"Shortlisted for {job.title} - {company.email}"
            html = f"""
            <h2>Congratulations! You've been shortlisted</h2>
            <p>Dear {student.name},</p>
            <p>You have been shortlisted for the position of <strong>{job.title}</strong> at <strong>{company.email}</strong>.</p>
            <p>Your profile match: {score_student_for_job(student, job).get('overall_match_percentage', 0)}%</p>
            <p>Please log in to the placement portal to view more details and apply if interested.</p>
            <p>Best regards,<br>Placement Portal Team</p>
            """
            background_tasks.add_task(send_email, student.owner_email, subject, html)

    # Generic notification to all students
    student_users = db.query(StudentUser).all()
    if student_users:
        subject = f"Shortlist generated for {job.title}"
        html = f"""
        <h2>New job shortlist available</h2>
        <p>A shortlist was generated for the job <strong>{job.title}</strong> by <strong>{company.email}</strong>.</p>
        <p>Please log in to the placement portal to see if you were selected.</p>
        """
        for u in student_users:
            if not any(student.owner_email == u.email for student in shortlisted_students):
                background_tasks.add_task(send_email, u.email, subject, html)

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
    """Log when a company views a student's profile."""
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    
    # Log the view
    profile_view = ProfileView(
        student_id=student_id,
        viewer_email=company.email,
        viewer_role="company"
    )
    db.add(profile_view)
    
    # Notify the student
    notification = Notification(
        student_email=student.owner_email,
        message=f"Your profile was viewed by {company.email} (Company)"
    )
    db.add(notification)
    
    db.commit()
    return {"message": "Profile view logged"}


@router.get("/student/{student_id}")
def get_student_profile(
    student_id: int,
    company=Depends(company_required),
    db: Session = Depends(get_db)
):
    """Get student profile details for company viewing."""
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    
    # Log the profile view
    profile_view = ProfileView(
        student_id=student_id,
        viewer_email=company.email,
        viewer_role="company"
    )
    db.add(profile_view)
    
    # Notify the student
    notification = Notification(
        student_email=student.owner_email,
        message=f"Your profile was viewed by {company.email} (Company)"
    )
    db.add(notification)
    
    db.commit()
    
    return {
        "id": student.id,
        "name": student.name,
        "skills": student.skills,
        "cgpa": student.cgpa,
        "resume_url": student.resume_url,
        "has_resume": bool(student.resume_url)
    }
