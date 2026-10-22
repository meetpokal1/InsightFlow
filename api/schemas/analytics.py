from pydantic import BaseModel, Field


class CategoryPerformance(BaseModel):
    category_name: str
    revenue: float
    profit: float
    margin_pct: float | None
    revenue_last_12m: float | None
    revenue_prior_12m: float | None
    growth_pct: float | None = Field(description="Last 12 months against the 12 months before")
    share_pct: float | None = Field(description="Share of revenue in the last 12 months")
    share_change_pts: float | None = Field(description="Change in revenue share, in points")
    trend: str = Field(description="Declining, Gaining share, Losing share or Steady")
