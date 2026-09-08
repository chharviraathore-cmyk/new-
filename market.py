"""
market.py — KisanPay market intelligence module.

No-API version: reads only from the Supabase 'market_prices' table.
Skips Agmarknet entirely — no AGMARKNET_API_KEY, no network dependency,
one less thing to break during a live demo.

IMPORTANT: every function here does pure arithmetic on real numbers.
Nothing in this file calls Gemini or any AI model. The AI (ai.py's
generate_market_advice) only ever phrases a result computed here —
it never calculates a price, average, or trend itself.
"""

import os
import pandas as pd
from datetime import date, timedelta
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


def get_market_prices(crop):
    """
    Return (dataframe, source) of cached prices for a crop.
    source is always 'cached' in this version — kept as a return value
    so app.py code that unpacks (df, _source) doesn't need to change.
    """
    result = (
        supabase.table("market_prices")
        .select("*")
        .eq("crop", crop)
        .order("price_date", desc=False)
        .execute()
    )
    df = pd.DataFrame(result.data)
    return df, "cached"


def get_latest_price(crop, mandi_name=None):
    """Most recent price for a crop, optionally at a specific mandi."""
    df, _ = get_market_prices(crop)
    if df.empty:
        return None
    if mandi_name:
        df = df[df["mandi_name"] == mandi_name]
        if df.empty:
            return None
    latest_date = df["price_date"].max()
    row = df[df["price_date"] == latest_date].iloc[0]
    return float(row["price_per_quintal"])


def get_price_trend(crop, mandi_name=None, days=7):
    """
    Last N days of prices as a DataFrame with columns [price_date, price_per_quintal].
    Returns an empty DataFrame (with those columns) if there's no data —
    never a bare list, so app.py's .empty check and .groupby() both work.
    """
    df, _ = get_market_prices(crop)
    if df.empty:
        return pd.DataFrame(columns=["price_date", "price_per_quintal"])
    if mandi_name:
        df = df[df["mandi_name"] == mandi_name]
    df = df.sort_values("price_date").tail(days)
    return df[["price_date", "price_per_quintal"]].reset_index(drop=True)


def compare_mandis(crop):
    """
    Latest price per mandi for a crop, as a DataFrame with columns
    [mandi_name, price_per_quintal, price_date], sorted high to low.
    """
    df, _ = get_market_prices(crop)
    if df.empty:
        return pd.DataFrame(columns=["mandi_name", "price_per_quintal", "price_date"])
    latest_per_mandi = df.sort_values("price_date").groupby("mandi_name").last().reset_index()
    latest_per_mandi = latest_per_mandi.sort_values("price_per_quintal", ascending=False)
    return latest_per_mandi[["mandi_name", "price_per_quintal", "price_date"]]


def check_price_alert(crop, mandi_name=None):
    """
    Pure arithmetic — compares latest price to the 7-day average.
    Returns a dict: {"status": "high"|"low"|"normal"|"unknown", "latest": float, "avg": float, "pct_diff": float}
    "unknown" means there isn't enough price history yet to say anything —
    ai.py handles that case by telling the farmer honestly instead of guessing.
    """
    trend_df = get_price_trend(crop, mandi_name, days=7)
    if trend_df.empty or len(trend_df) < 2:
        return {"status": "unknown", "latest": None, "avg": None, "pct_diff": None}

    prices = trend_df["price_per_quintal"].tolist()
    latest = prices[-1]
    avg = sum(prices) / len(prices)

    if avg == 0:
        return {"status": "unknown", "latest": latest, "avg": avg, "pct_diff": None}

    pct_diff = round((latest - avg) / avg * 100, 1)
    if pct_diff > 5:
        status = "high"
    elif pct_diff < -5:
        status = "low"
    else:
        status = "normal"

    return {"status": status, "latest": round(latest, 2), "avg": round(avg, 2), "pct_diff": pct_diff}


def estimate_profit(quantity_quintals, market_price, your_price):
    """
    Compares what the farmer actually got vs. what they'd have gotten at market price.
    Returns {"difference": signed_number, "better_than_market": bool}.
    difference is positive when the farmer did BETTER than market, negative when worse —
    app.py takes abs() itself when displaying the "below market" case.
    """
    market_total = quantity_quintals * market_price
    your_total = quantity_quintals * your_price
    diff = round(your_total - market_total, 2)
    return {"difference": diff, "better_than_market": diff >= 0}


def get_all_crops_trend(crops, days=14):
    """
    Pure arithmetic across several crops at once — no AI involved.

    For each crop, combines check_price_alert() (latest vs 7-day avg) with a
    simple rising/falling read on the last `days` of prices: split the window
    in half and compare the two halves' averages. This is the only "trend
    direction" signal in the app — Gemini never computes it, it only phrases it.

    Returns: {crop: {..fields from check_price_alert.., "trend_direction": "rising"|"falling"|"stable"|"unknown", "slope_pct": float|None}}
    """
    results = {}
    for crop in crops:
        alert = check_price_alert(crop)
        trend_df = get_price_trend(crop, days=days)

        trend_direction = "unknown"
        slope_pct = None
        if len(trend_df) >= 4:
            prices = trend_df["price_per_quintal"].tolist()
            mid = len(prices) // 2
            first_half_avg = sum(prices[:mid]) / mid
            second_half_avg = sum(prices[mid:]) / (len(prices) - mid)
            if first_half_avg > 0:
                slope_pct = round((second_half_avg - first_half_avg) / first_half_avg * 100, 1)
                if slope_pct > 3:
                    trend_direction = "rising"
                elif slope_pct < -3:
                    trend_direction = "falling"
                else:
                    trend_direction = "stable"

        results[crop] = {**alert, "trend_direction": trend_direction, "slope_pct": slope_pct}
    return results


def compute_personal_insight(alert, last_sale):
    """
    Pure arithmetic comparing a farmer's own last recorded sale for a crop
    against today's market numbers (from check_price_alert). No DB or AI
    calls in here — same rule as the rest of this file: this only computes,
    ai.py only phrases.

    alert: dict from check_price_alert().
    last_sale: dict from db.get_last_sale_for_crop() — expected to have
    'buyer_name', 'price_per_quintal', and 'created_at' keys, but any of
    them can be missing/None.

    Returns None when there's nothing meaningful to compare (no history yet,
    the last sale's price per quintal couldn't be computed because the
    logged quantity wasn't parseable, or today's price is unknown) — that
    way callers can just skip personalization instead of showing a broken
    comparison.
    """
    if not last_sale or alert.get("status") == "unknown":
        return None

    last_price = last_sale.get("price_per_quintal")
    latest = alert.get("latest")
    if not last_price or not latest:
        return None

    pct_vs_last_sale = round((latest - last_price) / last_price * 100, 1)

    days_ago = None
    created_at = last_sale.get("created_at")
    if created_at:
        try:
            sold_date = pd.to_datetime(created_at).date()
            days_ago = (date.today() - sold_date).days
        except Exception:
            days_ago = None

    return {
        "last_price": last_price,
        "last_buyer": last_sale.get("buyer_name"),
        "days_ago": days_ago,
        "pct_vs_last_sale": pct_vs_last_sale,
        "better_now": pct_vs_last_sale > 0,
    }


def seed_demo_data(crop_data):
    """
    Manually seed market_prices with realistic numbers — no API needed.

    crop_data format:
    {
        "Wheat": {
            "Delhi Azadpur Mandi": 2350,
            "Karnal Mandi": 2280,
            "Sonipat Mandi": 2310,
        },
        "Onion": {
            "Delhi Azadpur Mandi": 1800,
            "Lasalgaon Mandi": 1650,
        },
    }

    For each mandi, generates a small realistic 7-day trend ending at the
    given price (±2-3% daily jitter) so the trend chart has something to show.
    """
    import random
    random.seed(42)  # reproducible — same "random" trend every time you reseed

    rows = []
    today = date.today()
    for crop, mandis in crop_data.items():
        for mandi_name, end_price in mandis.items():
            price = end_price
            daily_prices = [price]
            for _ in range(6):
                price = price / (1 + random.uniform(-0.03, 0.03))
                daily_prices.append(price)
            daily_prices = list(reversed(daily_prices))  # oldest -> newest
            for i, p in enumerate(daily_prices):
                rows.append({
                    "crop": crop,
                    "mandi_name": mandi_name,
                    "price_per_quintal": round(p, 2),
                    "price_date": str(today - timedelta(days=6 - i)),
                    "source": "manual_seed",
                })

    supabase.table("market_prices").insert(rows).execute()
    print(f"Seeded {len(rows)} rows across {len(crop_data)} crops.")


if __name__ == "__main__":
    # Quick self-test — run `python market.py` after seeding to sanity-check.
    df, source = get_market_prices("Wheat")
    print(f"Wheat prices ({source}):")
    print(df)
    print("Alert:", check_price_alert("Wheat"))
    print("Mandi comparison:")
    print(compare_mandis("Wheat"))
    print("Profit estimate (10 quintal, sold at 2400, market 2350):")
    print(estimate_profit(10, 2350, 2400))
