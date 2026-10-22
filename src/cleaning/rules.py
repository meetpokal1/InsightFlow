"""Business rules used by the cleaning code.

Limits and vocabularies live here so a rule like "more than 500 units on one line is
suspicious" is changed in one place.
"""

from datetime import date

# Day-first on purpose: this is an Indian business, so 05/03/2025 means 5 March.
DATE_FORMATS = ["%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%d/%m/%Y", "%d-%b-%Y"]
ORDER_DATE_MIN = date(2020, 1, 1)

MAX_ORDER_QUANTITY = 500
# a unit price more than 3x above or below the list price is treated as a typing error
PRICE_OUTLIER_RATIO = 3.0

UNCATEGORIZED_ID = "CAT99"
UNCATEGORIZED_NAME = "Uncategorized"
# cost as a share of price, used when neither the product nor its category has any data
DEFAULT_COST_RATIO = 0.75

CUSTOMER_TYPES = {
    "retail": "Retail",
    "retailer": "Retail",
    "wholesale": "Wholesale",
    "wholesaler": "Wholesale",
    "corporate": "Corporate",
    "corp": "Corporate",
}
DEFAULT_CUSTOMER_TYPE = "Retail"

ORDER_STATUSES = {
    "completed": "Completed",
    "complete": "Completed",
    "cancelled": "Cancelled",
    "canceled": "Cancelled",
    "returned": "Returned",
    "return": "Returned",
}

PAYMENT_METHODS = {
    "upi": "UPI",
    "cash": "Cash",
    "credit card": "Credit Card",
    "cc": "Credit Card",
    "debit card": "Debit Card",
    "net banking": "Net Banking",
    "netbanking": "Net Banking",
    "credit terms": "Credit Terms",
}
DEFAULT_PAYMENT_METHOD = "Unknown"

# old or alternative spellings -> official city name
CITY_ALIASES = {
    "bombay": "Mumbai",
    "bangalore": "Bengaluru",
    "bengalore": "Bengaluru",
    "calcutta": "Kolkata",
    "madras": "Chennai",
    "new delhi": "Delhi",
    "poona": "Pune",
}

VALID_REGIONS = {"North", "South", "East", "West", "Central"}
VALID_LOCATION_TYPES = {"Store", "Warehouse"}
VALID_ORDER_STATUSES = {"Completed", "Cancelled", "Returned"}
VALID_CUSTOMER_TYPES = {"Retail", "Wholesale", "Corporate"}
