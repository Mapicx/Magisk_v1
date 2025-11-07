from pydantic import BaseModel

class ResumeBase(BaseModel):
    filename: str
    file_url: str

class ResumeCreate(ResumeBase):
    pass

class ResumeResponse(ResumeBase):
    id: int

    class Config:
        orm_mode = True
