import os
import io
import json
from dotenv import load_dotenv
load_dotenv()
from openai import OpenAI

# ---- Groq client (OpenAI-compatible API, completely free tier, no card needed) ----
GROQ_API_KEY = os.environ["GROQ_API_KEY"]
client = OpenAI(api_key=GROQ_API_KEY, base_url="https://api.groq.com/openai/v1")

TEXT_MODEL = "openai/gpt-oss-120b"   # Groq's current free-tier chat model
WHISPER_MODEL = "whisper-large-v3"   # Groq's free speech-to-text model


def _clean_json(text: str) -> str:
    return text.strip().strip("```json").strip("```").strip()


def _generate_text(prompt: str) -> str:
    response = client.chat.completions.create(
        model=TEXT_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.4,
    )
    return response.choices[0].message.content.strip()


def extract_transaction(spoken_text: str) -> dict:
    """Turns a Hindi/Hinglish sentence into structured transaction fields."""
    prompt = f"""
Extract transaction details from this farmer's statement and return ONLY valid JSON,
no markdown, no explanation. Fields: buyer_name, crop, quantity, amount, payment_status
("paid" or "pending" — if not mentioned, use "pending" and add a field "needs_followup": true).

Statement: "{spoken_text}"

Example output:
{{"buyer_name": "Ramesh", "crop": "wheat", "quantity": "3 quintal", "amount": 9000, "payment_status": "pending", "needs_followup": true}}
"""
    text = _generate_text(prompt)
    return json.loads(_clean_json(text))


def explain_in_words(fact: str, language_hint: str = "simple Hindi") -> str:
    """Turns a raw fact/number into a spoken-style sentence. Always pass the model the REAL number — never let it guess."""
    prompt = f"Explain this financial fact to a farmer in simple, everyday {language_hint}, in one short friendly sentence: {fact}"
    return _generate_text(prompt)


def extract_transaction_from_audio(audio_bytes: bytes, mime_type: str = "audio/wav", language: str = "Hindi") -> dict:
    """
    Transcribes the recording with Groq's Whisper, then extracts transaction
    fields from that transcript with a text call. (Groq's chat models can't
    take raw audio directly the way Gemini could, so this is two calls
    instead of one — but it's still a single free API key.)
    """
    ext = mime_type.split("/")[-1] if "/" in mime_type else "wav"
    audio_file = io.BytesIO(audio_bytes)
    audio_file.name = f"recording.{ext}"  # Groq's SDK needs a filename to infer format

    transcript_resp = client.audio.transcriptions.create(
        model=WHISPER_MODEL,
        file=audio_file,
        # language left unset so Whisper auto-detects — Indian regional
        # languages/dialects vary and Whisper's auto-detect handles this well
    )
    heard_text = transcript_resp.text.strip()

    prompt = f"""
This is a transcript of a farmer's spoken statement, likely in {language} (an Indian
regional language/dialect). Extract transaction details and return ONLY valid JSON,
no markdown, no explanation. Fields: buyer_name, crop, quantity, amount, payment_status
("paid" or "pending" — if not mentioned, use "pending" and add a field "needs_followup": true).

Transcript: "{heard_text}"

Example output:
{{"buyer_name": "Ramesh", "crop": "wheat", "quantity": "3 quintal", "amount": 9000, "payment_status": "pending", "needs_followup": true}}
"""
    text = _generate_text(prompt)
    data = json.loads(_clean_json(text))
    data["heard_text"] = heard_text
    return data


def generate_market_advice(
    alert_info: dict,
    crop: str,
    language_hint: str = "Hindi",
    personal_insight: dict = None,
) -> str:
    """
    Turns a price-alert dict (from market.check_price_alert) into a short,
    farmer-friendly spoken-style suggestion. Same rule as explain_in_words:
    the model only phrases numbers that were already computed in Python —
    it never calculates the numbers itself.

    alert_info example: {"status": "high", "latest": 2400, "avg": 2150, "pct_diff": 11.6}

    personal_insight (optional): dict from market.compute_personal_insight().
    When given, the sentence is grounded in the farmer's OWN last sale for
    this crop instead of staying generic — e.g. whether today's price beats
    what they personally got last time, not just the crop's average.
    """
    status = alert_info.get("status")
    latest = alert_info.get("latest")
    avg = alert_info.get("avg")
    pct = alert_info.get("pct_diff")

    if status == "unknown":
        prompt = (
            f"In {language_hint}, write one short, simple sentence telling a farmer "
            f"that there isn't enough price data yet for {crop} to give advice. "
            f"Keep it under 20 words, no English words mixed in."
        )
    else:
        direction = "above" if status == "high" else "below" if status == "low" else "close to"

        personal_bit = ""
        word_limit = 25
        if personal_insight:
            days_ago = personal_insight.get("days_ago")
            days_bit = f"{days_ago} days ago" if days_ago is not None else "recently"
            move = "higher" if personal_insight["better_now"] else "lower"
            buyer = personal_insight.get("last_buyer") or "a buyer"
            personal_bit = (
                f" This same farmer personally sold {crop} to {buyer} {days_bit} at "
                f"₹{personal_insight['last_price']} per quintal — today's price is "
                f"{abs(personal_insight['pct_vs_last_sale'])}% {move} than that. "
                f"Weave this personal comparison naturally into the sentence, using only "
                f"these numbers — don't just repeat the crop average separately."
            )
            word_limit = 35

        prompt = (
            f"A farmer is asking about {crop} prices. Today's price is ₹{latest} per quintal, "
            f"the recent average is ₹{avg}, which is {pct}% {direction} average.{personal_bit} "
            f"In {language_hint}, write ONE short, plain-spoken sentence (under {word_limit} words) "
            f"telling the farmer whether this looks like a good time to sell or buy, "
            f"based only on these numbers. Do not invent any other numbers or facts."
        )

    return _generate_text(prompt)


def generate_crop_advisory(market_data: dict, financial_data: dict, language_hint: str = "Hindi") -> str:
    """
    Turns already-computed market trend data (market.get_all_crops_trend) and
    already-computed financial data (wallet balance, pending dues) into one
    spoken-style advisory in the farmer's language.

    Same rule as the rest of this file: every NUMBER below was computed in
    plain Python. The model only phrases them, and is allowed to add general,
    well-known agronomic/seasonal knowledge (typical sowing windows etc.) —
    but is explicitly told not to invent any price, percentage, or rupee figure.

    market_data: {crop: {"status", "latest", "avg", "pct_diff", "trend_direction", "slope_pct"}}
    financial_data: {"wallet_balance": float, "total_pending": float, "total_paid": float}
    """
    lines = [
        f"Farmer's wallet balance: Rs {financial_data.get('wallet_balance', 0):,.2f}",
        f"Total owed to farmer by buyers (pending): Rs {financial_data.get('total_pending', 0):,.2f}",
        f"Total collected so far: Rs {financial_data.get('total_paid', 0):,.2f}",
        "",
    ]

    for crop, d in market_data.items():
        if d.get("status") == "unknown":
            lines.append(f"{crop}: not enough price history yet.")
            continue
        trend_bit = f", recent trend: {d['trend_direction']}"
        if d.get("slope_pct") is not None:
            trend_bit += f" ({d['slope_pct']}% over the period)"
        lines.append(
            f"{crop}: latest Rs {d['latest']}/quintal, 7-day avg Rs {d['avg']}/quintal "
            f"({d['pct_diff']}% vs avg){trend_bit}"
        )

    data_block = "\n".join(lines)

    prompt = f"""
You are advising an Indian smallholder farmer, speaking in {language_hint}. Use ONLY the
numbers given below — never invent a price, percentage, or rupee amount that isn't listed here.

DATA:
{data_block}

Write a short, warm, plain-spoken advisory (120-180 words, no bullet points, no markdown,
in {language_hint} only, no English words mixed in) that:
1. Opens with one line on how their money situation looks right now (wallet balance and
   pending dues together).
2. For any crop marked "rising", mentions this could be a good time to sell if they're
   holding stock — using only the numbers given.
3. For any crop marked "falling", says it may be worth waiting or checking other mandis —
   using only the numbers given.
4. Adds ONE general, well-known seasonal farming tip relevant to whichever crops are listed
   (e.g. typical sowing or harvest timing for that crop) — make clear this is general
   seasonal knowledge, not something calculated from today's prices.
5. Ends with one encouraging sentence.

Do not mention any AI provider or that this was generated by a program.
"""
    return _generate_text(prompt)


if __name__ == "__main__":
    # Quick manual test: run `python ai.py`
    print(extract_transaction("Ramesh ko 3 quintal gehun 9000 mein diya"))

    # Test market advice with fake alert data (no network/DB needed)
    fake_alert = {"status": "high", "latest": 2400, "avg": 2150, "pct_diff": 11.6}
    print(generate_market_advice(fake_alert, "Wheat", language_hint="Hindi"))
