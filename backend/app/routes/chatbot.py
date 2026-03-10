from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from ..deps import student_required, get_db
from ..models import Student
from ..utils.resume_chatbot import resume_chatbot

router = APIRouter(prefix="/chatbot", tags=["Resume Chatbot"])


class ChatRequest(BaseModel):
    question: str
    has_resume: bool = False


class ChatResponse(BaseModel):
    question: str
    answer: str
    has_resume: bool
    analysis: Optional[dict] = None


@router.post("/chat", response_model=ChatResponse)
def chat_with_resume_bot(
    chat_request: ChatRequest,
    student=Depends(student_required),
    db: Session = Depends(get_db)
):
    """
    Chat with AI resume review bot for profile improvement.
    """
    try:
        # Get student profile data
        profile = db.query(Student).filter(Student.owner_email == student.email).first()
        profile_data = None
        
        if profile:
            profile_data = {
                "full_name": profile.name,
                "skills": profile.skills,
                "cgpa": profile.cgpa,
                "resume_url": profile.resume_url,
                "profile_completion": 0  # Will be calculated if needed
            }
        
        # Get chatbot response
        response = resume_chatbot.chat_with_resume(
            question=chat_request.question,
            pdf_content=None,  # Resume content handled separately
            profile_data=profile_data
        )
        
        return ChatResponse(**response)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chatbot error: {str(e)}")


@router.post("/chat-with-resume", response_model=ChatResponse)
def chat_with_resume_analysis(
    chat_request: ChatRequest,
    file: UploadFile = File(...),
    student=Depends(student_required),
    db: Session = Depends(get_db)
):
    """
    Chat with AI resume review bot using uploaded resume for analysis.
    """
    # Validate file
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    
    if file.size and file.size > 2 * 1024 * 1024:  # 2MB limit
        raise HTTPException(status_code=400, detail="File size exceeds 2MB limit")
    
    try:
        # Read file content
        pdf_content = file.file.read()
        
        # Get student profile data
        profile = db.query(Student).filter(Student.owner_email == student.email).first()
        profile_data = None
        
        if profile:
            profile_data = {
                "full_name": profile.name,
                "skills": profile.skills,
                "cgpa": profile.cgpa,
                "resume_url": profile.resume_url,
                "profile_completion": 0
            }
        
        # Get chatbot response with resume analysis
        response = resume_chatbot.chat_with_resume(
            question=chat_request.question,
            pdf_content=pdf_content,
            profile_data=profile_data
        )
        
        return ChatResponse(**response)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Resume analysis failed: {str(e)}")


@router.get("/suggestions")
def get_resume_suggestions(
    student=Depends(student_required),
    db: Session = Depends(get_db)
):
    """
    Get general resume improvement suggestions based on profile.
    """
    try:
        profile = db.query(Student).filter(Student.owner_email == student.email).first()
        
        if not profile:
            return {
                "message": "Create your profile first to get personalized suggestions",
                "suggestions": [
                    "Add your full name and contact information",
                    "List your technical skills and programming languages",
                    "Include your educational background and CGPA",
                    "Upload your resume for detailed analysis"
                ]
            }
        
        # Get profile-based suggestions
        suggestions = []
        
        # Check profile completeness
        if not profile.name or not profile.name.strip():
            suggestions.append("📝 Add your full name to make your profile professional")
        
        if not profile.skills or len(profile.skills.split(',')) < 3:
            suggestions.append("💡 Add more technical skills (aim for 5+ skills)")
        
        if not profile.cgpa or profile.cgpa < 6.0:
            suggestions.append("📚 Highlight your academic achievements and projects")
        
        if not profile.resume_url:
            suggestions.append("📄 Upload your resume for better job matching")
        
        # Skills-based suggestions
        if profile.skills:
            skills_text = profile.skills.lower()
            if not any(skill in skills_text for skill in ['python', 'java', 'javascript']):
                suggestions.append("🐍 Add popular programming languages like Python, Java, or JavaScript")
            
            if not any(skill in skills_text for skill in ['aws', 'docker', 'kubernetes']):
                suggestions.append("☁️ Consider learning cloud technologies (AWS, Docker) - they're in high demand")
        
        if not suggestions:
            suggestions = [
                "🎉 Your profile looks great! Consider adding more details about your projects and achievements.",
                "📈 Regularly update your profile with new skills and experiences.",
                "🔍 Use specific keywords that match your target job descriptions."
            ]
        
        return {
            "profile_completion": "Complete" if all([profile.name, profile.skills, profile.cgpa, profile.resume_url]) else "Incomplete",
            "suggestions": suggestions,
            "next_steps": [
                "Upload your resume for detailed AI analysis",
                "Ask me specific questions about improving your profile",
                "Check out matched jobs for your skills"
            ]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get suggestions: {str(e)}")


@router.get("/skills-analysis")
def get_skills_analysis(
    student=Depends(student_required),
    db: Session = Depends(get_db)
):
    """
    Get analysis of skills from student's profile.
    """
    try:
        profile = db.query(Student).filter(Student.owner_email == student.email).first()
        
        if not profile or not profile.skills:
            return {
                "message": "Add skills to your profile to see analysis",
                "skills_breakdown": {},
                "recommendations": [
                    "Add programming languages you know",
                    "Include frameworks and libraries",
                    "List tools and technologies you're familiar with"
                ]
            }
        
        # Analyze skills using chatbot
        skills_text = profile.skills.lower()
        skills_found = resume_chatbot.extract_skills(skills_text)
        
        total_skills = sum(len(skills_list) for skills_list in skills_found.values())
        
        recommendations = []
        
        if total_skills < 5:
            recommendations.append("Add more specific technical skills to increase visibility")
        
        if 'cloud_devops' not in skills_found:
            recommendations.append("Consider adding cloud/DevOps skills (AWS, Docker, etc.)")
        
        if 'programming_languages' not in skills_found:
            recommendations.append("Include specific programming languages")
        
        return {
            "total_skills": total_skills,
            "skills_breakdown": {
                category.replace('_', ' ').title(): skills_list
                for category, skills_list in skills_found.items()
            },
            "all_skills_list": profile.skills.split(','),
            "recommendations": recommendations,
            "skill_density": "High" if total_skills >= 8 else "Medium" if total_skills >= 4 else "Low"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Skills analysis failed: {str(e)}")
