from collections import Counter
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..deps import admin_required, get_db
from ..models import Student, Job, AdminUser, CompanyUser, StudentUser, ProfileView, Notification
from ..matching import score_student_for_job
from ..utils.database_cleanup import run_full_cleanup
from ..utils.email import send_email

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
def shortlist_students(
    job_id: int, 
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db), 
    admin=Depends(admin_required)
):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

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
                message=f"You were shortlisted for {job.title} by Placement Cell!"
            )
            db.add(notification)
            
            # Send email
            subject = f"Shortlisted for {job.title} - Placement Cell"
            html = f"""
            <h2>Congratulations! You've been shortlisted</h2>
            <p>Dear {student.name},</p>
            <p>You have been shortlisted for the position of <strong>{job.title}</strong> by the Placement Cell.</p>
            <p>Your profile match: {score_student_for_job(student, job).get('overall_match_percentage', 0)}%</p>
            <p>Please log in to the placement portal to view more details.</p>
            <p>Best regards,<br>Placement Cell Team</p>
            """
            background_tasks.add_task(send_email, student.owner_email, subject, html)

    db.commit()

    return {
        "job": job.title,
        "results": ranked,
        "shortlisted_count": len(shortlisted_students),
        "total_students": len(students)
    }


@router.get("/profile-views-analytics")
def profile_views_analytics(admin=Depends(admin_required), db: Session = Depends(get_db)):
    """Get comprehensive profile view analytics."""
    
    # Total profile views
    total_views = db.query(ProfileView).count()
    
    # Views by role
    views_by_role = db.query(
        ProfileView.viewer_role,
        func.count(ProfileView.id).label('count')
    ).group_by(ProfileView.viewer_role).all()
    
    # Most viewed students
    most_viewed = db.query(
        ProfileView.student_id,
        func.count(ProfileView.id).label('view_count')
    ).group_by(ProfileView.student_id).order_by(func.count(ProfileView.id).desc()).limit(10).all()
    
    # Get student details for most viewed
    most_viewed_details = []
    for student_id, view_count in most_viewed:
        student = db.query(Student).filter(Student.id == student_id).first()
        if student:
            most_viewed_details.append({
                "student_id": student_id,
                "name": student.name,
                "email": student.owner_email,
                "view_count": view_count,
                "has_resume": bool(student.resume_url)
            })
    
    # Recent views
    recent_views = db.query(ProfileView).order_by(ProfileView.viewed_at.desc()).limit(20).all()
    
    recent_views_details = []
    for view in recent_views:
        student = db.query(Student).filter(Student.id == view.student_id).first()
        if student:
            recent_views_details.append({
                "student_name": student.name,
                "viewer_email": view.viewer_email,
                "viewer_role": view.viewer_role,
                "viewed_at": view.viewed_at.isoformat()
            })
    
    return {
        "total_profile_views": total_views,
        "views_by_role": [{"role": role, "count": count} for role, count in views_by_role],
        "most_viewed_students": most_viewed_details,
        "recent_views": recent_views_details
    }


@router.post("/profile/view/{student_id}")
def log_admin_profile_view(
    student_id: int,
    admin=Depends(admin_required),
    db: Session = Depends(get_db)
):
    """Log when admin views a student's profile."""
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    
    # Log the view
    profile_view = ProfileView(
        student_id=student_id,
        viewer_email=admin.email,
        viewer_role="admin"
    )
    db.add(profile_view)
    
    # Notify the student
    notification = Notification(
        student_email=student.owner_email,
        message=f"Your profile was viewed by Placement Cell"
    )
    db.add(notification)
    
    db.commit()
    return {"message": "Profile view logged"}


@router.get("/student/{student_id}")
def get_student_profile_for_admin(
    student_id: int,
    admin=Depends(admin_required),
    db: Session = Depends(get_db)
):
    """Get student profile details for admin viewing."""
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    
    # Log the profile view
    profile_view = ProfileView(
        student_id=student_id,
        viewer_email=admin.email,
        viewer_role="admin"
    )
    db.add(profile_view)
    
    # Notify the student
    notification = Notification(
        student_email=student.owner_email,
        message=f"Your profile was viewed by Placement Cell"
    )
    db.add(notification)
    
    db.commit()
    
    # Get profile view statistics
    view_stats = db.query(ProfileView).filter(ProfileView.student_id == student_id).all()
    
    return {
        "id": student.id,
        "name": student.name,
        "email": student.owner_email,
        "skills": student.skills,
        "cgpa": student.cgpa,
        "resume_url": student.resume_url,
        "has_resume": bool(student.resume_url),
        "profile_views": {
            "total_views": len(view_stats),
            "views_by_role": {
                role: len([v for v in view_stats if v.viewer_role == role])
                for role in ["admin", "company", "student"]
            },
            "recent_views": [
                {
                    "viewer_email": v.viewer_email,
                    "viewer_role": v.viewer_role,
                    "viewed_at": v.viewed_at.isoformat()
                }
                for v in view_stats[-5:]  # Last 5 views
            ]
        }
    }


@router.get("/analytics")
def admin_analytics(admin=Depends(admin_required), db: Session = Depends(get_db)):
    """Aggregate placement portal analytics for admin dashboard."""
    total_students = db.query(Student).count()
    total_jobs = db.query(Job).count()
    total_admins = db.query(AdminUser).count()
    total_companies = db.query(CompanyUser).count()
    total_student_users = db.query(StudentUser).count()

    total_users = total_admins + total_companies + total_student_users

    # Approximate total_shortlists as total potential matches (students x jobs)
    students = db.query(Student).all()
    jobs = db.query(Job).all()
    total_shortlists = 0
    for job in jobs:
        for s in students:
            scoring = score_student_for_job(s, job)
            score_val = scoring if isinstance(scoring, (int, float)) else scoring.get("score", 0)
            if score_val and score_val > 0:
                total_shortlists += 1

    # Time-based stats - without created_at columns we cannot be precise.
    # These are placeholders and will show 0 unless timestamps are added later.
    jobs_posted_today = 0
    new_users_today = 0

    # Top skills from Student.skills (comma-separated)
    skill_counter: Counter[str] = Counter()
    for s in students:
        if not s.skills:
            continue
        for raw in s.skills.split(","):
            skill = raw.strip().lower()
            if skill:
                skill_counter[skill] += 1

    top_skills = [
        {"skill": skill, "count": count}
        for skill, count in skill_counter.most_common(10)
    ]

    return {
        "total_users": total_users,
        "total_students": total_students,
        "total_companies": total_companies,
        "total_jobs": total_jobs,
        "total_shortlists": total_shortlists,
        "jobs_posted_today": jobs_posted_today,
        "new_users_today": new_users_today,
        "top_skills": top_skills,
    }


@router.post("/cleanup-database")
def cleanup_database(admin=Depends(admin_required), db: Session = Depends(get_db)):
    """Clean up duplicate profiles, unverified users, and orphaned data."""
    try:
        cleanup_report = run_full_cleanup(db)
        
        return {
            "message": "Database cleanup completed successfully",
            "report": cleanup_report
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cleanup failed: {str(e)}")

