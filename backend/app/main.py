import os
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .database import Base, engine
from .routes import students, jobs, auth, admin, company, student

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Placement Cell Portal API")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # dev only
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(students.router)
app.include_router(jobs.router)
app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(company.router)
app.include_router(student.router)

@app.get("/")
def home():
    return {"message": "Placement Portal API is running"}
