from pydantic import BaseModel
from typing import Optional

class ResumeBase(BaseModel):
    filename: str
    file_url: str
    linkedin_url: Optional[str] = None
    github_url: Optional[str] = None
    leetcode_url: Optional[str] = None

class ResumeCreate(ResumeBase):
    pass

class ResumeResponse(ResumeBase):
    id: int

    class Config:
        orm_mode = True
