from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from sqlalchemy.orm import Session
from typing import Optional

from ..deps import student_required, get_db
from ..models import Student, Job
from ..utils.ats_analyzer import ats_analyzer

router = APIRouter(prefix="/resume", tags=["Resume Analysis"])


@router.post("/analyze")
def analyze_resume(
    file: UploadFile = File(...),
    student=Depends(student_required),
    db: Session = Depends(get_db)
):
    """
    Perform comprehensive ATS analysis of uploaded resume.
    """
    # Validate file type
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Only PDF files are supported for ATS analysis")
    
    # Check file size (2MB limit)
    content = file.file.read()
    if len(content) > 2 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File size exceeds 2MB limit")
    
    try:
        # Perform ATS analysis
        analysis = ats_analyzer.analyze_resume(content)
        
        return {
            "message": "Resume analysis completed successfully",
            "analysis": analysis,
            "file_info": {
                "filename": file.filename,
                "size": len(content),
                "type": file.content_type
            }
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Resume analysis failed: {str(e)}")


@router.post("/score/{job_id}")
def score_resume_for_job(
    job_id: int,
    file: UploadFile = File(...),
    student=Depends(student_required),
    db: Session = Depends(get_db)
):
    """
    Score resume against specific job requirements.
    """
    # Validate job exists
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Validate file type
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    
    # Check file size
    content = file.file.read()
    if len(content) > 2 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File size exceeds 2MB limit")
    
    try:
        # Perform job-specific analysis
        analysis = ats_analyzer.analyze_resume(content, job.requirements)
        
        # Add job-specific context
        result = {
            "message": "Resume scored successfully for job",
            "job_info": {
                "id": job.id,
                "title": job.title,
                "requirements": job.requirements,
                "min_cgpa": job.min_cgpa
            },
            "analysis": analysis
        }
        
        # Add specific recommendations for this job
        if analysis['missing_keywords']:
            result["job_specific_recommendations"] = [
                f"Add these key skills from job description: {', '.join(analysis['missing_keywords'][:5])}"
            ]
        
        return result
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Resume scoring failed: {str(e)}")


@router.get("/skills-extractor")
def get_skills_extractor_info():
    """
    Get information about skills categories and keywords used by the ATS analyzer.
    """
    return {
        "skills_categories": ats_analyzer.TECH_SKILLS,
        "action_verbs": ats_analyzer.ACTION_VERBS,
        "quantitative_indicators": ats_analyzer.QUANTITATIVE_INDICATORS,
        "total_skills_tracked": len(ats_analyzer.all_skills)
    }


@router.post("/profile-analysis")
def analyze_student_profile(
    student=Depends(student_required),
    db: Session = Depends(get_db)
):
    """
    Analyze student's profile data for ATS optimization.
    """
    profile = db.query(Student).filter(Student.owner_email == student.email).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Student profile not found")
    
    # Analyze profile text
    profile_text = f"{profile.name} {profile.skills}".lower()
    
    # Extract skills from profile
    skills_found = ats_analyzer.extract_skills(profile_text)
    
    # Generate suggestions
    suggestions = []
    
    if not skills_found:
        suggestions.append("Add specific technical skills to your profile")
    else:
        total_skills = sum(len(skills) for skills in skills_found.values())
        if total_skills < 3:
            suggestions.append("Add more technical skills to improve your profile visibility")
        
        if 'programming_languages' not in skills_found:
            suggestions.append("Include programming languages you're proficient in")
        
        if len(profile.skills.split(',')) < 5:
            suggestions.append("Be more specific with your skills (e.g., 'Python, Django, PostgreSQL' instead of just 'Python')")
    
    # Calculate profile completeness score
    completeness_score = 0
    if profile.name and profile.name.strip():
        completeness_score += 2.5
    if profile.skills and len(profile.skills.split(',')) >= 3:
        completeness_score += 2.5
    if profile.cgpa and profile.cgpa > 0:
        completeness_score += 2.5
    if profile.resume_url:
        completeness_score += 2.5
    
    return {
        "profile_completeness": round(completeness_score, 1),
        "skills_found": skills_found,
        "total_skills_identified": sum(len(skills) for skills in skills_found.values()),
        "suggestions": suggestions,
        "profile_strength": "Strong" if completeness_score >= 7.5 else "Moderate" if completeness_score >= 5.0 else "Needs Improvement"
    }
