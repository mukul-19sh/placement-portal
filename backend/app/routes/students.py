import shutil
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, Request, status
from sqlalchemy.orm import Session
from typing import List

from ..database import SessionLocal
from ..models import Student
from ..schemas import StudentCreate
from ..deps import student_required

router = APIRouter(prefix="/students", tags=["Students"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/", summary="Add Students")
def add_students_bulk(students: List[StudentCreate], db: Session = Depends(get_db)):
    created: list[Student] = []

    for s in students:
        new_student = Student(**s.dict())
        db.add(new_student)
        created.append(new_student)

    db.commit()
    for s in created:
        db.refresh(s)

    return {
        "message": "Students added successfully",
        "count": len(created),
        "students": [
            {"id": s.id, "name": s.name, "skills": s.skills, "cgpa": s.cgpa, "resume_url": s.resume_url}
            for s in created
        ],
    }


@router.get("/")
def get_students(db: Session = Depends(get_db)):
    return db.query(Student).all()


RESUME_DIR = Path("uploads") / "resumes"
RESUME_DIR.mkdir(parents=True, exist_ok=True)


@router.post("/upload-resume/{student_id}", summary="Upload resume PDF for a student")
def upload_resume(
    student_id: int,
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_student=Depends(student_required),
):
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only PDF files are allowed")

    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found")

    filename = f"{student_id}_{uuid4().hex}.pdf"
    file_path = RESUME_DIR / filename

    with file_path.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    base = str(request.base_url).rstrip("/")
    student.resume_url = f"{base}/uploads/resumes/{filename}"
    db.add(student)
    db.commit()
    db.refresh(student)

    return {"message": "Resume uploaded successfully", "resume_url": student.resume_url}
