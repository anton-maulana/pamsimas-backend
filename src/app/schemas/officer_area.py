from pydantic import BaseModel, Field

class OfficerAreaBase(BaseModel):
    rt: int = Field(...)
    rw: int = Field(...)

class OfficerAreaCreate(OfficerAreaBase):
    pass

class OfficerAreaRead(OfficerAreaBase):
    id: int
    user_id: int

    class Config:
        from_attributes = True
