from enum import Enum

from pydantic import BaseModel, Field


class RiskStatus(str, Enum):
    out_of_stock = "Out of stock"
    stock_out_risk = "Stock-out risk"
    low_stock = "Low stock"


class LowStockItem(BaseModel):
    product_id: str
    product_name: str
    category_name: str
    location_id: str
    location_name: str
    quantity_on_hand: int
    reorder_level: int
    avg_daily_units: float = Field(description="Average units sold per day in the last 90 days")
    days_of_cover: float | None = Field(
        description="Days the stock lasts at the current sales rate"
    )
    lead_time_days: int = Field(description="Supplier lead time")
    stock_status: str
    suggested_order_qty: float = Field(
        description="Units to order to cover the lead time plus 30 more days of sales"
    )
