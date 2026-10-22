from datetime import date

from pydantic import BaseModel, ConfigDict, Field


class SalesSummary(BaseModel):
    """Headline numbers for completed orders in the selected period."""

    total_revenue: float = Field(description="Net revenue after discounts, in rupees")
    total_profit: float = Field(description="Net revenue minus cost of goods")
    margin_pct: float | None = Field(description="Profit as a percentage of revenue")
    total_orders: int
    total_customers: int = Field(description="Customers with at least one completed order")
    avg_order_value: float | None = Field(description="Revenue divided by the number of orders")
    units_sold: int
    inventory_value: float = Field(
        description="Cost value of the stock on hand at the latest snapshot (not date filtered)"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "total_revenue": 209034798.31,
                "total_profit": 42355329.09,
                "margin_pct": 20.3,
                "total_orders": 7878,
                "total_customers": 780,
                "avg_order_value": 26533.99,
                "units_sold": 1111322,
                "inventory_value": 22493991.1,
            }
        }
    )


class MonthlySales(BaseModel):
    month: date = Field(description="First day of the month")
    orders: int
    revenue: float
    profit: float
    margin_pct: float | None
    avg_order_value: float | None
    mom_growth_pct: float | None = Field(
        description="Revenue change against the previous month in the result (empty for the first)"
    )
