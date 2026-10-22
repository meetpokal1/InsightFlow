from enum import Enum

from pydantic import BaseModel, Field


class ProductMetric(str, Enum):
    revenue = "revenue"
    profit = "profit"
    units = "units"


class TopProduct(BaseModel):
    rank: int
    product_id: str
    product_name: str
    category_name: str
    units_sold: int
    revenue: float
    profit: float
    margin_pct: float | None = Field(description="Profit as a percentage of revenue")
