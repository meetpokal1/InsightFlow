from pydantic import BaseModel, Field


class TopCustomer(BaseModel):
    rank: int
    customer_id: str
    customer_name: str
    customer_type: str
    city: str | None
    orders: int
    revenue: float
    revenue_share_pct: float = Field(description="Share of all revenue in the selected period")
