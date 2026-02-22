from pydantic import BaseModel
from typing import List

class StudentCreate(BaseModel):
    name: str
    skills: str
    cgpa: float
