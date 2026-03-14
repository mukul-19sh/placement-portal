import shutil
from pathlib import Path
from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile, status, Query
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import BaseModel

from ..deps import student_required, get_db
from ..models import Job, Student, Notification, ProfileView, JobApplication, Interview, Offer, CompanyProfile
from ..schemas import StudentProfile
from ..matching import score_student_for_job
from ..utils.storage import storage_manager

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


def calculate_profile_completion(profile):
    """Calculate profile completion percentage."""
    if not profile:
        return 0
    
    completion = 0
    total_fields = 6  # name, skills, cgpa, resume, linkedin, github
    
    if profile.name and profile.name.strip():
        completion += 1
    if profile.skills and profile.skills.strip():
        completion += 1
    if profile.cgpa is not None and profile.cgpa > 0:
        completion += 1
    if profile.resume_url and profile.resume_url.strip():
        completion += 1
    if getattr(profile, 'linkedin_url', None) and profile.linkedin_url.strip():
        completion += 1
    if getattr(profile, 'github_url', None) and profile.github_url.strip():
        completion += 1
    
    return round((completion / total_fields) * 100)


@router.get("/profile")
def get_profile(student=Depends(student_required), db: Session = Depends(get_db)):
    """Return the current student's profile, if it exists."""
    profile = db.query(Student).filter(Student.owner_email == student.email).first()
    if not profile:
        return {
            "profile_completion": 0,
            "completion_status": "No profile created"
        }
    
    completion_percentage = calculate_profile_completion(profile)
    
    return {
        "id": profile.id,
        "full_name": profile.name,
        "skills": profile.skills,
        "cgpa": profile.cgpa,
        "resume_url": profile.resume_url,
        "linkedin_url": profile.linkedin_url,
        "github_url": profile.github_url,
        "profile_completion": completion_percentage,
        "completion_status": get_completion_status(completion_percentage)
    }


def get_completion_status(percentage):
    """Get completion status message based on percentage."""
    if percentage >= 100:
        return "Complete"
    elif percentage >= 75:
        return "Almost Complete"
    elif percentage >= 50:
        return "Half Complete"
    elif percentage >= 25:
        return "Started"
    else:
        return "Incomplete"


@router.post("/profile")
def create_or_update_student_profile(
    profile: StudentProfile,
    student=Depends(student_required),
    db: Session = Depends(get_db)
):
    """Create or update student profile (LinkedIn-style - one profile per email)."""
    
    # Check if profile already exists for this email
    existing_profile = db.query(Student).filter(Student.owner_email == student.email).first()
    
    if existing_profile:
        # Update existing profile
        existing_profile.name = profile.full_name
        existing_profile.skills = profile.skills
        existing_profile.cgpa = profile.cgpa
        existing_profile.linkedin_url = profile.linkedin_url
        existing_profile.github_url = profile.github_url
        db.commit()
        db.refresh(existing_profile)
        
        return {
            "message": "Profile updated successfully",
            "profile": existing_profile,
            "is_new": False
        }
    else:
        # Create new profile
        new_profile = Student(
            name=profile.full_name,
            skills=profile.skills,
            cgpa=profile.cgpa,
            owner_email=student.email,
            linkedin_url=profile.linkedin_url,
            github_url=profile.github_url
        )
        db.add(new_profile)
        db.commit()
        db.refresh(new_profile)
        
        return {
            "message": "Profile created successfully",
            "profile": new_profile,
            "is_new": True
        }


@router.post("/upload-resume")
def upload_resume_student(
    file: UploadFile = File(...),
    student=Depends(student_required),
    db: Session = Depends(get_db),
):
    """Upload resume for the current student using cloud storage."""
    profile = db.query(Student).filter(Student.owner_email == student.email).first()
    if not profile:
        raise HTTPException(status_code=400, detail="Create your profile before uploading a resume")

    # Read file content
    file_content = file.file.read()
    
    try:
        # Upload using storage manager
        file_url, storage_path = storage_manager.upload_file(
            file_content, file.filename, folder="resumes"
        )
        
        # Delete old resume if exists
        if profile.resume_url:
            storage_manager.delete_file(profile.resume_url)
        
        # Update profile with new resume URL
        profile.resume_url = file_url
        db.commit()
        db.refresh(profile)

        return {
            "message": "Resume uploaded successfully", 
            "resume_url": file_url,
            "storage_type": storage_manager.storage_type
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Resume upload failed: {str(e)}")


@router.get("/resume/download")
def download_resume(
    student=Depends(student_required),
    db: Session = Depends(get_db)
):
    """Get download URL for student's resume."""
    profile = db.query(Student).filter(Student.owner_email == student.email).first()
    if not profile or not profile.resume_url:
        raise HTTPException(status_code=404, detail="Resume not found")
    
    return {
        "download_url": profile.resume_url,
        "filename": f"resume_{profile.name.replace(' ', '_')}.pdf"
    }


@router.post("/profile/view/{student_id}")
def log_profile_view(
    student_id: int,
    viewer=Depends(student_required),
    db: Session = Depends(get_db)
):
    """Log when a student views another student's profile."""
    # Only allow students to view other students' profiles
    if viewer.email == db.query(Student).filter(Student.id == student_id).first().owner_email:
        raise HTTPException(status_code=400, detail="Cannot view your own profile")
    
    # Log the view
    profile_view = ProfileView(
        student_id=student_id,
        viewer_email=viewer.email,
        viewer_role="student"
    )
    db.add(profile_view)
    
    # Notify the viewed student
    viewed_student = db.query(Student).filter(Student.id == student_id).first()
    notification = Notification(
        student_email=viewed_student.owner_email,
        message=f"Your profile was viewed by {viewer.email}"
    )
    db.add(notification)
    
    db.commit()
    return {"message": "Profile view logged"}


@router.get("/profile-views")
def get_profile_views(
    student=Depends(student_required),
    db: Session = Depends(get_db)
):
    """Get profile views for the current student."""
    profile = db.query(Student).filter(Student.owner_email == student.email).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    views = db.query(ProfileView).filter(ProfileView.student_id == profile.id).all()
    
    return {
        "total_views": len(views),
        "views": [
            {
                "viewer_email": view.viewer_email,
                "viewer_role": view.viewer_role,
                "viewed_at": view.viewed_at.isoformat()
            }
            for view in views
        ]
    }


@router.get("/matched-jobs")
def get_matched_jobs(
    student=Depends(student_required), 
    db: Session = Depends(get_db),
    threshold: int = 70
):
    """Get jobs that match student profile above threshold percentage."""
    profile = db.query(Student).filter(Student.owner_email == student.email).first()
    if not profile:
        raise HTTPException(status_code=400, detail="Create your profile first")
    
    jobs = db.query(Job).all()
    matched_jobs = []
    
    for job in jobs:
        scoring = score_student_for_job(profile, job)
        match_percentage = scoring["overall_match_percentage"]
        
        if match_percentage >= threshold:
            matched_jobs.append({
                "id": job.id,
                "title": job.title,
                "requirements": job.requirements,
                "min_cgpa": job.min_cgpa,
                "match_percentage": match_percentage,
                "matched_skills": scoring["matched_skills"],
                "missing_skills": scoring["missing_skills"],
                "cgpa_eligible": scoring["cgpa_eligible"],
                "can_apply": True
            })
    
    # Sort by match percentage descending
    matched_jobs.sort(key=lambda x: x["match_percentage"], reverse=True)
    
    return {
        "matched_jobs": matched_jobs,
        "total_matched": len(matched_jobs),
        "threshold_used": threshold,
        "profile_completion": calculate_profile_completion(profile)
    }


@router.get("/resume/score/{job_id}")
def resume_score(job_id: int, student=Depends(student_required), db: Session = Depends(get_db)):
    profile = db.query(Student).filter(Student.owner_email == student.email).first()
    if not profile:
        raise HTTPException(status_code=400, detail="Create your profile first")
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    scoring = score_student_for_job(profile, job)
    skill_score = scoring["score"]
    matched = scoring["matched_skills"]
    missing = scoring["missing_skills"]

    # Normalize skill_score to 0-10 range roughly
    ats_score = min(10.0, max(0.0, skill_score / 20.0))

    suggestions = []
    if missing:
        suggestions.append("Consider adding these keywords to your resume: " + ", ".join(missing))
    if ats_score < 7:
        suggestions.append("Try to better align your skills and experience with the job requirements.")
    if profile.cgpa < job.min_cgpa:
        suggestions.append(f"Your CGPA is below the job's minimum ({job.min_cgpa}). Focus on roles with lower CGPA threshold.")

    return {
        "score": round(ats_score, 1),
        "matched_keywords": matched,
        "missing_keywords": missing,
        "suggestions": suggestions or ["Your profile already matches this job quite well."],
    }


@router.post("/apply/{job_id}")
def apply_job(
    job_id: int,
    student=Depends(student_required),
    db: Session = Depends(get_db),
):
    """Apply for a job if student meets the 70% match threshold."""
    profile = db.query(Student).filter(Student.owner_email == student.email).first()
    if not profile:
        raise HTTPException(status_code=400, detail="Create your profile first")
    
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Check if already applied
    existing_application = db.query(JobApplication).filter(
        JobApplication.student_email == student.email,
        JobApplication.job_id == job_id
    ).first()
    
    if existing_application:
        raise HTTPException(status_code=400, detail="You have already applied for this job")
    
    # Calculate match percentage
    scoring = score_student_for_job(profile, job)
    match_percentage = scoring["overall_match_percentage"]
    
    # Check if meets threshold
    if match_percentage < 70:
        raise HTTPException(
            status_code=400, 
            detail=f"Your profile matches {match_percentage}% which is below the 70% threshold required to apply"
        )
    
    # Create application
    application = JobApplication(
        student_email=student.email,
        job_id=job_id,
        match_percentage=match_percentage
    )
    
    db.add(application)
    
    # Create notification
    notification = Notification(
        student_email=student.email,
        message=f"Successfully applied for {job.title} with {match_percentage}% match"
    )
    db.add(notification)
    
    db.commit()
    
    return {
        "message": "Application submitted successfully",
        "job_title": job.title,
        "match_percentage": match_percentage,
        "application_id": application.id
    }


@router.get("/my-applications")
def get_my_applications(
    student=Depends(student_required),
    db: Session = Depends(get_db)
):
    """Get all applications made by the student with full detail."""
    applications = db.query(JobApplication).filter(
        JobApplication.student_email == student.email
    ).order_by(JobApplication.applied_at.desc()).all()

    STATUS_LABELS = {
        "applied":      "📋 Applied",
        "under_review": "🔍 Under Review",
        "shortlisted":  "⭐ Shortlisted",
        "interview":    "📅 Interview Scheduled",
        "rejected":     "❌ Rejected",
        "offer":        "🎉 Offer Received",
    }

    result = []
    for app in applications:
        job = db.query(Job).filter(Job.id == app.job_id).first()
        if not job:
            continue

        # Company name
        company_profile = db.query(CompanyProfile).filter(CompanyProfile.owner_email == job.created_by).first()
        company_name = company_profile.company_name if company_profile else (job.created_by or "Company")

        # Interview details
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

        # Offer details
        offer = db.query(Offer).filter(Offer.application_id == app.id).first()
        offer_info = None
        if offer:
            offer_info = {
                "id": offer.id,
                "position": offer.position,
                "ctc": offer.ctc,
                "status": offer.status,
                "company": company_name,
            }

        result.append({
            "application_id": app.id,
            "job_id": job.id,
            "job_title": job.title,
            "company": company_name,
            "applied_at": app.applied_at.isoformat(),
            "status": app.status,
            "status_label": STATUS_LABELS.get(app.status, app.status),
            "match_percentage": app.match_percentage,
            "interview": interview_info,
            "offer": offer_info,
        })

    return {"applications": result}


class OfferResponse(BaseModel):
    action: str  # "accept" | "reject"


@router.post("/offers/{offer_id}/respond")
def respond_to_offer(
    offer_id: int,
    body: OfferResponse,
    student=Depends(student_required),
    db: Session = Depends(get_db)
):
    """Student accepts or rejects a job offer."""
    if body.action not in ("accept", "reject"):
        raise HTTPException(status_code=400, detail="action must be 'accept' or 'reject'")

    offer = db.query(Offer).filter(
        Offer.id == offer_id,
        Offer.student_email == student.email
    ).first()
    if not offer:
        raise HTTPException(status_code=404, detail="Offer not found")

    if offer.status != "pending":
        raise HTTPException(status_code=400, detail="Offer already responded to")

    offer.status = body.action + "ed"  # "accepted" or "rejected"

    # Find the application and update its status
    app = db.query(JobApplication).filter(JobApplication.id == offer.application_id).first()
    if app:
        app.status = "offer_" + body.action + "ed"  # offer_accepted / offer_rejected

    # Notify the student themselves
    action_label = "accepted 🎉" if body.action == "accept" else "rejected"
    db.add(Notification(
        student_email=student.email,
        message=f"You {action_label} the offer for {offer.position} at {offer.company_email}"
    ))

    db.commit()
    return {"message": f"Offer {action_label}", "offer_id": offer_id, "new_status": offer.status}


@router.post("/ai-resume-review")
def ai_resume_review(
    job_id: int = None,
    student=Depends(student_required),
    db: Session = Depends(get_db),
):
    """AI-powered resume review with detailed feedback."""
    profile = db.query(Student).filter(Student.owner_email == student.email).first()
    if not profile:
        raise HTTPException(status_code=400, detail="Create your profile first")
    
    if not profile.resume_url:
        raise HTTPException(status_code=400, detail="Please upload your resume first")
    
    # Get job if job_id provided
    job = None
    job_specific_feedback = []
    if job_id:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
    
    # AI Resume Analysis (simulated - in production would use actual AI service)
    analysis = analyze_resume_content(profile, job)
    
    # Create notification for review completion
    notification = Notification(
        student_email=student.email,
        message=f"AI resume review completed. Overall score: {analysis['overall_score']}/10"
    )
    db.add(notification)
    db.commit()
    
    return {
        "overall_score": analysis["overall_score"],
        "strengths": analysis["strengths"],
        "improvements": analysis["improvements"],
        "skill_analysis": analysis["skill_analysis"],
        "formatting_tips": analysis["formatting_tips"],
        "job_specific_feedback": job_specific_feedback,
        "next_steps": analysis["next_steps"]
    }


def analyze_resume_content(profile, job=None):
    """Simulated AI resume analysis."""
    strengths = []
    improvements = []
    skill_analysis = {}
    formatting_tips = []
    next_steps = []
    
    # Analyze skills
    if profile.skills:
        skills_list = [s.strip() for s in profile.skills.split(",")]
        skill_count = len(skills_list)
        
        if skill_count >= 5:
            strengths.append(f"Good variety of skills listed ({skill_count} skills)")
            skill_analysis["diversity"] = "Good"
        else:
            improvements.append(f"Consider adding more relevant skills (currently {skill_count})")
            skill_analysis["diversity"] = "Needs improvement"
        
        # Check for in-demand skills
        tech_skills = ["python", "java", "javascript", "react", "node.js", "sql", "aws", "docker"]
        found_tech = [skill for skill in skills_list if skill.lower() in tech_skills]
        
        if found_tech:
            strengths.append(f"Contains in-demand technical skills: {', '.join(found_tech)}")
            skill_analysis["technical_skills"] = "Strong"
        else:
            improvements.append("Consider adding more in-demand technical skills")
            skill_analysis["technical_skills"] = "Needs enhancement"
    
    # Analyze CGPA
    if profile.cgpa:
        if profile.cgpa >= 8.0:
            strengths.append(f"Strong academic performance (CGPA: {profile.cgpa})")
        elif profile.cgpa >= 6.0:
            improvements.append(f"Consider highlighting projects to complement CGPA of {profile.cgpa}")
        else:
            improvements.append(f"Focus on showcasing practical skills and projects")
    
    # Job-specific analysis
    if job:
        job_skills = [s.strip().lower() for s in job.requirements.split(",")]
        profile_skills = [s.strip().lower() for s in profile.skills.split(",")]
        
        matched_skills = set(profile_skills) & set(job_skills)
        match_percentage = (len(matched_skills) / len(job_skills)) * 100 if job_skills else 0
        
        if match_percentage >= 70:
            strengths.append(f"Strong match for {job.title}: {match_percentage:.1f}% skill alignment")
        else:
            improvements.append(f"Skill alignment for {job.title} could be improved: {match_percentage:.1f}%")
    
    # Formatting tips
    formatting_tips.extend([
        "Use clear section headers (Education, Skills, Experience, Projects)",
        "Quantify achievements with numbers and metrics",
        "Keep resume to 1-2 pages maximum",
        "Use action verbs to start bullet points",
        "Proofread carefully for typos and grammatical errors"
    ])
    
    # Next steps
    next_steps.extend([
        "Update your profile with any missing information",
        "Upload a polished resume PDF",
        "Apply for jobs that match 70% or higher",
        "Prepare for interviews based on your skills"
    ])
    
    # Calculate overall score
    score = 5.0  # Base score
    
    if profile.name and profile.name.strip():
        score += 0.5
    if profile.skills and len(profile.skills.split(",")) >= 5:
        score += 1.5
    if profile.cgpa and profile.cgpa >= 7.0:
        score += 1.0
    if profile.resume_url:
        score += 1.0
    if job and len(set(profile.skills.split(",")) & set(job.requirements.split(","))) / len(job.requirements.split(",")) >= 0.7:
        score += 1.0
    
    overall_score = min(10.0, score)
    
    return {
        "overall_score": round(overall_score, 1),
        "strengths": strengths or ["Resume profile created"],
        "improvements": improvements or ["Continue enhancing your profile"],
        "skill_analysis": skill_analysis,
        "formatting_tips": formatting_tips,
        "next_steps": next_steps
    }


@router.post("/notifications/{notification_id}/read")
def mark_notification_read(
    notification_id: int,
    student=Depends(student_required),
    db: Session = Depends(get_db)
):
    """Mark a specific notification as read."""
    notification = db.query(Notification).filter(
        Notification.id == notification_id,
        Notification.student_email == student.email
    ).first()
    
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    
    notification.is_read = True
    db.commit()
    
    return {"message": "Notification marked as read"}


@router.post("/notifications/mark-all-read")
def mark_all_notifications_read(
    student=Depends(student_required),
    db: Session = Depends(get_db)
):
    """Mark all notifications as read for the student."""
    db.query(Notification).filter(
        Notification.student_email == student.email,
        Notification.is_read == False
    ).update({"is_read": True})
    
    db.commit()
    
    return {"message": "All notifications marked as read"}


@router.get("/notifications")
def student_notifications(student=Depends(student_required), db: Session = Depends(get_db)):
    notifs = (
        db.query(Notification)
        .filter(Notification.student_email == student.email)
        .order_by(Notification.created_at.desc())
        .all()
    )
    return [
        {
            "id": n.id,
            "message": n.message,
            "created_at": n.created_at.isoformat(),
            "is_read": n.is_read,
        }
        for n in notifs
    ]
