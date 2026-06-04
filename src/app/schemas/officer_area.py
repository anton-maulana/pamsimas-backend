from pydantic import BaseModel, Field

class OfficerAreaBase(BaseModel):
    rt: str = Field(..., max_length=10)
    rw: str = Field(..., max_length=10)

class OfficerAreaCreate(OfficerAreaBase):
    pass

class OfficerAreaRead(OfficerAreaBase):
    id: int
    user_id: int

    class Config:
        from_attributes = True
