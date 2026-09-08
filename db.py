import os
import re
from dotenv import load_dotenv
load_dotenv()
print("SUPABASE_URL:", os.getenv("SUPABASE_URL"))
print("SUPABASE_KEY found:", os.getenv("SUPABASE_KEY") is not None)
from supabase import create_client
import pandas as pd

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


def insert_transaction(farmer_id, buyer_name, crop, quantity, amount, payment_status="pending"):
    return supabase.table("transactions").insert({
        "farmer_id": farmer_id,
        "buyer_name": buyer_name,
        "crop": crop,
        "quantity": quantity,
        "amount": amount,
        "payment_status": payment_status,
    }).execute()


def get_all_transactions(farmer_id):
    res = supabase.table("transactions").select("*").eq("farmer_id", farmer_id).execute()
    return pd.DataFrame(res.data)


def get_hisab(farmer_id):
    """Returns per-buyer summary: total paid, total pending."""
    df = get_all_transactions(farmer_id)
    if df.empty:
        return pd.DataFrame()
    summary = df.groupby(["buyer_name", "payment_status"])["amount"].sum().unstack(fill_value=0)
    summary = summary.rename(columns={"paid": "Paid (₹)", "pending": "Pending (₹)"})
    return summary.reset_index()


def get_pending_for_buyer(farmer_id, buyer_name):
    df = get_all_transactions(farmer_id)
    if df.empty:
        return 0
    match = df[(df["buyer_name"].str.lower() == buyer_name.lower()) & (df["payment_status"] == "pending")]
    return match["amount"].sum()


def check_scam_shield(farmer_id, buyer_name, claimed_amount):
    """Returns True if a matching pending transaction exists — i.e. the payment claim is legit."""
    df = get_all_transactions(farmer_id)
    if df.empty:
        return False
    match = df[
        (df["buyer_name"].str.lower() == buyer_name.lower())
        & (df["payment_status"] == "pending")
        & (df["amount"] == claimed_amount)
    ]
    return not match.empty


# ---------------- Crop history (for personalized market advice) ----------------

def _parse_quantity_quintals(quantity):
    """
    Best-effort: pulls a numeric quintal figure out of the free-text
    'quantity' field (e.g. "3 quintal", "2.5"). Returns None (rather than
    guessing) when the unit looks like something other than quintals, or
    when there's no number to find at all — a wrong unit conversion would
    silently corrupt the price-per-quintal math downstream.
    """
    if quantity is None:
        return None
    s = str(quantity).lower()
    if "kg" in s or "kilo" in s or "ton" in s:
        return None
    match = re.search(r"[-+]?\d*\.?\d+", s)
    if not match:
        return None
    value = float(match.group())
    return value if value > 0 else None


def get_transactions_for_crop(farmer_id, crop):
    """
    This farmer's transactions for one crop, most recent first, with an
    added 'price_per_quintal' column computed from quantity + amount where
    the quantity could be parsed as quintals (else None for that row).
    """
    df = get_all_transactions(farmer_id)
    if df.empty or "crop" not in df:
        return pd.DataFrame()
    df = df[df["crop"].str.lower() == str(crop).lower()].copy()
    if df.empty:
        return df

    df["quantity_quintals"] = df["quantity"].apply(_parse_quantity_quintals)
    df["price_per_quintal"] = df.apply(
        lambda r: round(r["amount"] / r["quantity_quintals"], 2)
        if r["quantity_quintals"] else None,
        axis=1,
    )
    if "created_at" in df:
        df = df.sort_values("created_at", ascending=False)
    return df.reset_index(drop=True)


def get_last_sale_for_crop(farmer_id, crop):
    """
    The farmer's most recent transaction for this crop, as a plain dict
    (or None if they've never logged one). Used to personalize market advice
    — e.g. "you sold this to X, Y days ago, at this price".
    """
    df = get_transactions_for_crop(farmer_id, crop)
    if df.empty:
        return None
    return df.iloc[0].to_dict()


# ---------------- Payment wallet functions ----------------

def get_all_payments(farmer_id):
    res = supabase.table("payments").select("*").eq("farmer_id", farmer_id).execute()
    return pd.DataFrame(res.data)


def get_wallet_balance(farmer_id):
    """Wallet = money collected (type='collect') - money sent out (type='send')."""
    df = get_all_payments(farmer_id)
    if df.empty:
        return 0.0
    collected = df[df["type"] == "collect"]["amount"].sum()
    sent = df[df["type"] == "send"]["amount"].sum()
    return float(collected) - float(sent)


def get_pending_transactions(farmer_id):
    """Returns pending transactions as a list of dicts, for rendering 'collect' buttons."""
    df = get_all_transactions(farmer_id)
    if df.empty:
        return []
    pending = df[df["payment_status"] == "pending"]
    return pending.to_dict(orient="records")


def collect_payment(transaction_id, farmer_id, buyer_name, amount):
    """Mark a pending transaction as paid + log the cash-in as a payment."""
    supabase.table("transactions").update({"payment_status": "paid"}).eq("id", transaction_id).execute()
    return supabase.table("payments").insert({
        "farmer_id": farmer_id,
        "type": "collect",
        "party_name": buyer_name,
        "amount": amount,
        "linked_transaction_id": transaction_id,
    }).execute()


def send_payment(farmer_id, party_name, amount):
    """Send money out (e.g. paying an input dealer). Not linked to any transaction."""
    return supabase.table("payments").insert({
        "farmer_id": farmer_id,
        "type": "send",
        "party_name": party_name,
        "amount": amount,
        "linked_transaction_id": None,
    }).execute()


def get_payment_history(farmer_id):
    """Returns payment history (both collect and send), most recent first."""
    df = get_all_payments(farmer_id)
    if df.empty:
        return []
    df = df.sort_values("created_at", ascending=False)
    return df.to_dict(orient="records")


if __name__ == "__main__":
    # Quick manual test: run `python db.py` after adding a few rows in Supabase's table editor.
    print(get_hisab("farmer_1"))
    print("Wallet balance:", get_wallet_balance("farmer_1"))
    print("Pending transactions:", get_pending_transactions("farmer_1"))
    print("Payment history:", get_payment_history("farmer_1"))
