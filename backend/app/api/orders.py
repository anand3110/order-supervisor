from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import Order
from app.schemas.order import OrderCreate, OrderResponse


router = APIRouter(
    prefix="/api/orders",
    tags=["Orders"],
)


@router.post("/", response_model=OrderResponse)
def create_order(
    data: OrderCreate,
    db: Session = Depends(get_db),
):
    order = Order(
        customer_name=data.customer_name,
        amount=data.amount,
    )

    db.add(order)
    db.commit()
    db.refresh(order)

    return order