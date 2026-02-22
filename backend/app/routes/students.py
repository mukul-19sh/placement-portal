from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from ..database import SessionLocal
from ..models import Student
from ..schemas import StudentCreate

router = APIRouter(prefix="/students", tags=["Students"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/", summary="Add Students")
def add_students_bulk(students: List[StudentCreate], db: Session = Depends(get_db)):
    created = []

    for s in students:
        new_student = Student(**s.dict())
        db.add(new_student)
        created.append(new_student)

    db.commit()
    return {
        "message": "Students added successfully",
        "count": len(created)
    }


@router.get("/")
def get_students(db: Session = Depends(get_db)):
    return db.query(Student).all()
