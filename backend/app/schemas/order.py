from uuid import UUID

from pydantic import BaseModel


class OrderCreate(BaseModel):
    customer_name: str
    amount: float


class OrderResponse(BaseModel):
    id: UUID
    customer_name: str
    amount: float
    status: str

    class Config:
        from_attributes = True