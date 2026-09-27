from uuid import UUID

from pydantic import BaseModel


class SupervisorCreate(BaseModel):
    name: str
    base_instruction: str
    model: str = "gemini-3.7-flash"
    wake_policy: str = "important_events"


class SupervisorResponse(BaseModel):
    id: UUID
    name: str
    base_instruction: str
    model: str
    wake_policy: str

    class Config:
        from_attributes = True