import os
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from .database import Base, engine
from .routes import students, jobs, auth, admin, company, student, resume, chatbot

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Placement Cell Portal API")

# Add CORS middleware FIRST (before anything else)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost",
        "http://localhost:3000",
        "http://localhost:5500",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5500",
        "*", # Fallback
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# Include all routers
app.include_router(students.router)
app.include_router(jobs.router)
app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(company.router)
app.include_router(student.router)
app.include_router(resume.router)
app.include_router(chatbot.router)

@app.get("/")
def home():
    return {"message": "Placement Portal API is running"}

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "version": "2.0.0",
        "features": [
            "Email Verification",
            "Cloud Storage",
            "Profile Views Tracking",
            "ATS Resume Analysis",
            "Advanced Notifications",
            "Rate Limiting",
            "Security Headers"
        ]
    }


@app.get("/debug")
def debug_info():
    """Debug endpoint to check system status."""
    try:
        import PyPDF2
        pdf_status = "PyPDF2 available"
    except ImportError:
        pdf_status = "PyPDF2 not available"
    
    try:
        from app.utils.resume_chatbot import resume_chatbot
        chatbot_status = "Chatbot available"
    except ImportError as e:
        chatbot_status = f"Chatbot error: {e}"
    
    try:
        from app.utils.storage import storage_manager
        storage_status = f"Storage manager available (type: {storage_manager.storage_type})"
    except ImportError as e:
        storage_status = f"Storage error: {e}"
    
    return {
        "dependencies": {
            "pdf": pdf_status,
            "chatbot": chatbot_status,
            "storage": storage_status
        },
        "environment": {
            "use_cloud_storage": os.getenv("USE_CLOUD_STORAGE", "false"),
            "storage_type": os.getenv("STORAGE_TYPE", "local")
        }
    }
