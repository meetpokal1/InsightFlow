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
    replenishment_qty_required: int = Field(
        default=0,
        description="Units required to bring quantity_on_hand up to reorder_level: max(0, reorder_level - quantity_on_hand)",
    )
    replenishment_cost_estimate: float = Field(
        default=0.0,
        description="Capital required at cost price to bring stock to reorder level",
    )
    stock_gap_retail_val: float = Field(
        default=0.0,
        description="Retail valuation at list selling price of the replenishment quantity required",
    )
    is_stockout: bool = Field(
        default=False,
        description="True if quantity_on_hand is zero",
    )


class InventorySummaryResponse(BaseModel):
    total_positions: int
    total_inventory_value: float
    stockout_positions: int
    below_reorder_positions: int
    replenishment_units_required: int
    replenishment_cost_estimate: float
    stock_gap_retail_val: float
    suggested_order_units: int
