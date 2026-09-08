"""
seed_market.py — run this once to populate market_prices with demo data.

Usage (from inside your Kisanpay folder):
    py seed_market.py
"""

from market import seed_demo_data

seed_demo_data({
    "Wheat": {
        "Delhi Azadpur Mandi": 2350,
        "Karnal Mandi": 2280,
        "Sonipat Mandi": 2310,
    },
    "Onion": {
        "Delhi Azadpur Mandi": 1800,
        "Lasalgaon Mandi": 1650,
    },
})
