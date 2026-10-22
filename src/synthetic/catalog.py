"""Reference data for the made-up business: a mid-sized FMCG and office-supplies
distributor with eight outlets across India. Product names are generic (no real
brands) and all contact details use reserved .example / example.com domains.

The numbers are chosen so the data has a few real stories to find:
- staples (rice, oil, water, paper, notebooks) sell a lot at 4-9% margin
- a handful of products almost never sell
- Electronics Accessories and Snacks grow, Household Care and Stationery shrink
- October and November are festive-season peaks
- Kolkata and Jaipur are the weakest locations
"""

from datetime import date

DATA_START = date(2024, 10, 1)
DATA_END = date(2026, 9, 30)
INVENTORY_SNAPSHOT_DATE = DATA_END

# category_id -> (name, expected yearly growth in demand)
CATEGORIES = {
    "CAT01": ("Beverages", 0.08),
    "CAT02": ("Packaged Foods", 0.03),
    "CAT03": ("Snacks & Confectionery", 0.12),
    "CAT04": ("Household Care", -0.04),
    "CAT05": ("Personal Care", 0.06),
    "CAT06": ("Stationery & Office", -0.08),
    "CAT07": ("Electronics Accessories", 0.20),
}

# supplier_id -> (name, city, lead time in days, categories supplied)
SUPPLIERS = {
    "S01": ("Sunrise Beverages Pvt Ltd", "Mumbai", 5, ["CAT01"]),
    "S02": ("Coastal Drinks Co", "Chennai", 8, ["CAT01"]),
    "S03": ("Golden Harvest Foods", "Jaipur", 7, ["CAT02"]),
    "S04": ("Everfresh Staples Ltd", "Delhi", 10, ["CAT02", "CAT03"]),
    "S05": ("CrunchTime Snacks LLP", "Pune", 6, ["CAT03"]),
    "S06": ("CleanWave Household Pvt Ltd", "Mumbai", 9, ["CAT04"]),
    "S07": ("BrightHome Products", "Ahmedabad", 12, ["CAT04"]),
    "S08": ("PureGlow Personal Care", "Bengaluru", 14, ["CAT05"]),
    "S09": ("Skyline Cosmetics Ltd", "Hyderabad", 18, ["CAT05"]),
    "S10": ("PaperTrail Stationers", "Kolkata", 7, ["CAT06"]),
    "S11": ("OfficeEase Supplies", "Delhi", 11, ["CAT06"]),
    "S12": ("VoltEdge Accessories", "Bengaluru", 21, ["CAT07"]),
}

# location_id -> (city, state, region, type, share of customers and orders)
LOCATIONS = {
    "L01": ("Mumbai", "Maharashtra", "West", "Warehouse", 0.22),
    "L02": ("Delhi", "Delhi", "North", "Warehouse", 0.16),
    "L03": ("Bengaluru", "Karnataka", "South", "Warehouse", 0.16),
    "L04": ("Pune", "Maharashtra", "West", "Store", 0.10),
    "L05": ("Hyderabad", "Telangana", "South", "Store", 0.11),
    "L06": ("Chennai", "Tamil Nadu", "South", "Store", 0.09),
    "L07": ("Kolkata", "West Bengal", "East", "Store", 0.08),
    "L08": ("Jaipur", "Rajasthan", "North", "Store", 0.08),
}

# category -> [(name, unit, selling price in INR, margin, popularity)]
# margin = (price - cost) / price, popularity is a relative sales weight
PRODUCT_TEMPLATES = {
    "CAT01": [
        ("Orange Juice 1L", "carton", 120, 0.22, 1.0),
        ("Mango Nectar 1L", "carton", 110, 0.24, 0.9),
        ("Cola Soft Drink 2L", "bottle", 95, 0.18, 1.6),
        ("Green Tea Bags 100pk", "box", 280, 0.35, 0.6),
        ("Instant Coffee 200g", "jar", 450, 0.30, 0.8),
        ("Mineral Water 1L (12 Pack)", "pack", 180, 0.05, 2.2),
        ("Energy Drink 250ml", "can", 110, 0.32, 0.9),
        ("Lemon Iced Tea 500ml", "bottle", 55, 0.26, 0.8),
        ("Coconut Water 1L", "carton", 130, 0.28, 0.4),
    ],
    "CAT02": [
        ("Basmati Rice 5kg", "bag", 720, 0.05, 1.8),
        ("Sunflower Oil 1L", "bottle", 165, 0.04, 2.0),
        ("Whole Wheat Flour 5kg", "bag", 260, 0.06, 1.5),
        ("Toor Dal 1kg", "pack", 160, 0.08, 1.2),
        ("Pasta Penne 500g", "pack", 90, 0.20, 0.7),
        ("Tomato Ketchup 1kg", "bottle", 150, 0.27, 0.8),
        ("Instant Noodles 5 Pack", "pack", 70, 0.22, 1.4),
        ("Peanut Butter 400g", "jar", 240, 0.33, 0.5),
        ("Strawberry Jam 500g", "jar", 175, 0.30, 0.3),
    ],
    "CAT03": [
        ("Salted Potato Chips 150g", "pack", 50, 0.30, 1.8),
        ("Masala Peanuts 200g", "pack", 60, 0.28, 1.0),
        ("Chocolate Cookies 300g", "pack", 80, 0.26, 1.5),
        ("Dark Chocolate Bar 100g", "bar", 150, 0.38, 0.9),
        ("Trail Mix 250g", "pack", 220, 0.40, 0.5),
        ("Roasted Cashews 500g", "pack", 650, 0.25, 0.4),
        ("Cream Biscuits 400g", "pack", 55, 0.20, 1.7),
        ("Popcorn Kernels 500g", "pack", 95, 0.32, 0.3),
        ("Fruit Gummies 200g", "pack", 90, 0.35, 0.35),
    ],
    "CAT04": [
        ("Detergent Powder 1kg", "pack", 130, 0.07, 1.8),
        ("Dishwash Liquid 750ml", "bottle", 120, 0.22, 1.2),
        ("Floor Cleaner 1L", "bottle", 150, 0.25, 0.9),
        ("Toilet Cleaner 500ml", "bottle", 95, 0.24, 0.8),
        ("Garbage Bags 30 Pack", "pack", 110, 0.28, 0.7),
        ("Paper Towels 6 Rolls", "pack", 240, 0.30, 0.6),
        ("Glass Cleaner 500ml", "bottle", 110, 0.30, 0.4),
        ("Laundry Softener 1L", "bottle", 210, 0.33, 0.5),
        ("Scented Candles 3 Pack", "pack", 350, 0.45, 0.15),
    ],
    "CAT05": [
        ("Herbal Shampoo 340ml", "bottle", 280, 0.40, 1.1),
        ("Body Lotion 400ml", "bottle", 310, 0.42, 0.9),
        ("Whitening Toothpaste 150g", "tube", 110, 0.30, 1.6),
        ("Hand Wash Liquid 250ml", "bottle", 85, 0.28, 1.3),
        ("Bath Soap 4 Pack", "pack", 160, 0.20, 1.5),
        ("Face Wash 100ml", "tube", 220, 0.45, 0.8),
        ("Deodorant Spray 150ml", "can", 230, 0.44, 0.9),
        ("Sunscreen SPF50 100ml", "tube", 420, 0.48, 0.45),
        ("Electric Toothbrush Heads 4 Pack", "pack", 650, 0.50, 0.15),
    ],
    "CAT06": [
        ("A4 Copier Paper 500 Sheets", "ream", 380, 0.09, 1.8),
        ("Ruled Notebook 200 Pages", "piece", 70, 0.06, 1.7),
        ("Ballpoint Pens Blue 10 Pack", "pack", 90, 0.30, 1.4),
        ("Permanent Markers 4 Pack", "pack", 130, 0.35, 0.8),
        ("Stapler with Pins", "piece", 160, 0.38, 0.5),
        ("Desk Organizer", "piece", 450, 0.42, 0.25),
        ("Sticky Notes 12 Pack", "pack", 210, 0.37, 0.6),
        ("Fountain Pen Set", "set", 899, 0.46, 0.08),
    ],
    "CAT07": [
        ("USB-C Charging Cable 1m", "piece", 349, 0.45, 1.5),
        ("Wireless Mouse", "piece", 799, 0.32, 1.0),
        ("Bluetooth Earbuds", "pair", 1499, 0.28, 0.9),
        ("Power Bank 10000mAh", "piece", 1299, 0.30, 1.1),
        ("4-Port USB Hub", "piece", 699, 0.38, 0.25),
        ("Laptop Sleeve 15in", "piece", 899, 0.40, 0.3),
        ("HDMI Cable 3m", "piece", 399, 0.50, 0.12),
    ],
}

# relative order volume by calendar month (festive peak in Oct and Nov)
MONTH_SEASONALITY = {
    1: 0.95,
    2: 0.90,
    3: 1.00,
    4: 1.00,
    5: 1.05,
    6: 0.95,
    7: 0.90,
    8: 0.95,
    9: 1.00,
    10: 1.25,
    11: 1.20,
    12: 1.15,
}
OVERALL_ANNUAL_GROWTH = 0.10

CUSTOMER_TYPE_MIX = {"Retail": 0.70, "Wholesale": 0.20, "Corporate": 0.10}
# average number of orders over the full 24 months for a customer who is active throughout
CUSTOMER_TYPE_MEAN_ORDERS = {"Retail": 6.0, "Wholesale": 38.0, "Corporate": 14.0}
# (min, max) line items on one order
CUSTOMER_TYPE_ITEMS = {"Retail": (1, 4), "Wholesale": (3, 8), "Corporate": (2, 6)}
# order quantity per line: (median, sigma) of a lognormal distribution
CUSTOMER_TYPE_QTY = {"Retail": (2.0, 0.5), "Wholesale": (40.0, 0.6), "Corporate": (15.0, 0.6)}
CUSTOMER_TYPE_DISCOUNTS = {
    "Retail": [0, 0, 0, 0, 5],
    "Wholesale": [5, 8, 10, 12],
    "Corporate": [3, 5, 8],
}
# customer type -> (payment methods, probabilities)
PAYMENT_METHODS = {
    "Retail": (["UPI", "Cash", "Debit Card", "Credit Card"], [0.45, 0.20, 0.20, 0.15]),
    "Wholesale": (["Credit Terms", "Net Banking", "UPI"], [0.60, 0.25, 0.15]),
    "Corporate": (["Credit Terms", "Net Banking", "Credit Card"], [0.55, 0.30, 0.15]),
}
ORDER_STATUS_MIX = (["Completed", "Cancelled", "Returned"], [0.90, 0.06, 0.04])

# days of stock cover (low, high) for each inventory scenario
STOCK_SCENARIOS = {
    "healthy": (25, 70),
    "at_risk": (0.5, 6),
    "overstock": (200, 500),
    "stocked_out": (0, 0),
}
STOCK_SCENARIO_PROBS = [0.70, 0.12, 0.12, 0.06]

FIRST_NAMES = (
    "Aarav Anjali Rohan Priya Vikram Sneha Arjun Neha Karan Pooja "
    "Rahul Divya Amit Kavita Sanjay Meera Rajesh Ananya Nikhil Ritu "
    "Manish Swati Deepak Isha Suresh Nandini Varun Shreya Gaurav Tanvi"
).split()
LAST_NAMES = (
    "Sharma Patel Iyer Reddy Gupta Mehta Nair Singh Das Joshi "
    "Kulkarni Banerjee Verma Chopra Rao Shah Menon Bhatt Kapoor Desai"
).split()
TRADER_WORDS = ["Traders", "Enterprises", "Distributors", "Stores", "Agencies", "Wholesale Mart"]
COMPANY_WORDS = (
    "Apex Nimbus Vertex Orbit Lumen Zenith Pioneer Crest Helix Summit "
    "Quantum Meridian Horizon Catalyst Fulcrum"
).split()
COMPANY_SUFFIXES = ["Solutions Pvt Ltd", "Technologies Pvt Ltd", "Consulting LLP", "Services Ltd"]
EMAIL_DOMAINS = ["example.com", "example.org", "example.net"]
