from dotenv import load_dotenv
load_dotenv()  # reads .env into environment variables — must happen before db/ai imports below

import pandas as pd
import streamlit as st
from streamlit_mic_recorder import mic_recorder
from db import (
    insert_transaction,
    get_hisab,
    get_pending_for_buyer,
    check_scam_shield,
    get_wallet_balance,
    get_pending_transactions,
    collect_payment,
    send_payment,
    get_payment_history,
)
from ai import extract_transaction_from_audio, explain_in_words, generate_market_advice, generate_crop_advisory
from market import (
    get_market_prices,
    get_price_trend,
    compare_mandis,
    check_price_alert,
    estimate_profit,
    get_all_crops_trend,
)
from tts import text_to_speech_bytes
from rag import answer_farming_question
from translations import TRANSLATIONS, LANGUAGES
from styling import CUSTOM_CSS, buyer_card_html

st.set_page_config(page_title="KisanPay", layout="centered", page_icon="🌾")
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)
FARMER_ID = "farmer_1"  # hardcoded for demo

# ---- Language selection (drives EVERY string below) ----
if "language" not in st.session_state:
    st.session_state.language = "Hindi"

st.session_state.language = st.selectbox(
    "Apni bhasha chuniye / Choose your language:",
    LANGUAGES,
    index=LANGUAGES.index(st.session_state.language),
)
T = TRANSLATIONS[st.session_state.language]
GEMINI_LANG = T["gemini_hint"]

st.title(T["app_title"])

tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    T["tab_talk"], T["tab_hisab"], T["tab_ask"], T["tab_scam"],
    T.get("tab_payments", "💰 Payments"), T.get("tab_market", "📈 Market"),
    T.get("tab_advisor", "🌱 Advisor"),
])

# ---- Tab 1: Voice-first transaction entry ----
with tab1:
    st.subheader(T["talk_subheader"])
    audio = mic_recorder(start_prompt=T["mic_start"], stop_prompt=T["mic_stop"], format="wav", key="recorder")

    if "extracted" not in st.session_state:
        st.session_state.extracted = None

    if audio and audio.get("bytes"):
        st.audio(audio["bytes"])  # lets you replay what was recorded, useful for debugging
        with st.spinner(T["listening"]):
            st.session_state.extracted = extract_transaction_from_audio(
                audio["bytes"], mime_type="audio/wav", language=GEMINI_LANG
            )

    if st.session_state.extracted:
        data = st.session_state.extracted
        st.write(f"{T['heard_label']} {data.get('heard_text', '(no transcript)')}")
        st.json(data)
        if st.button(T["confirm_save"]):
            insert_transaction(
                FARMER_ID,
                data["buyer_name"],
                data.get("crop"),
                data.get("quantity"),
                data["amount"],
                data["payment_status"],
            )
            st.success(T["saved"])
            st.balloons()
            st.session_state.extracted = None

# ---- Tab 2: Hisab ledger ----
with tab2:
    st.subheader(T["hisab_subheader"])
    df = get_hisab(FARMER_ID)
    if df.empty:
        st.info(T["no_transactions"])
    else:
        for _, row in df.iterrows():
            paid = row.get("Paid (₹)", 0)
            pending = row.get("Pending (₹)", 0)
            st.markdown(buyer_card_html(row["buyer_name"], paid, pending), unsafe_allow_html=True)

# ---- Tab 3: Ask KisanPay ----
# Split into two clearly separate inputs — a past bug had farmers typing general
# questions into the buyer-name field, which produced a nonsense "answer" because
# that field was only ever wired to look up a specific buyer's pending amount.
with tab3:
    st.subheader(T["ask_subheader"])

    st.markdown(f"#### {T.get('check_buyer_header', 'Check What a Buyer Owes')}")
    buyer = st.text_input(T["buyer_label"], key="buyer_lookup_input")
    if st.button(T["ask_button"], key="buyer_lookup_btn") and buyer:
        pending = get_pending_for_buyer(FARMER_ID, buyer)
        answer = explain_in_words(f"{buyer} owes ₹{pending}", language_hint=GEMINI_LANG)
        st.write(answer)

    st.divider()

    st.markdown(f"#### {T.get('farming_question_header', '🌾 Ask a Farming Question')}")
    farming_question = st.text_input(
        T.get("farming_question_placeholder", "e.g. When should I sow wheat?"),
        key="farming_question_input",
    )
    if st.button(T.get("farming_ask_button", "Get Answer"), key="farming_ask_btn") and farming_question:
        with st.spinner(T.get("thinking", "Thinking it over...")):
            farming_answer = answer_farming_question(farming_question, language_hint=GEMINI_LANG)
        st.write(farming_answer)

# ---- Tab 4: Scam Shield ----
with tab4:
    st.subheader(T["scam_subheader"])
    check_buyer = st.text_input(T["scam_buyer_label"], key="scam_buyer")
    check_amount = st.number_input(T["scam_amount_label"], min_value=0, key="scam_amount")
    if st.button(T["verify_button"]):
        if check_scam_shield(FARMER_ID, check_buyer, check_amount):
            st.success(T["verified_msg"])
        else:
            st.error(T["not_verified_msg"])

# ---- Tab 5: Payments (wallet) ----
with tab5:
    st.subheader(T.get("payments_subheader", "Payments"))

    balance = get_wallet_balance(FARMER_ID)
    balance_color = "#2E7D32" if balance >= 0 else "#B00020"
    st.markdown(
        f"<h3>{T.get('wallet_balance', 'Wallet Balance')}</h3>"
        f"<h2 style='color:{balance_color}'>₹{balance:,.2f}</h2>",
        unsafe_allow_html=True,
    )

    col1, col2 = st.columns(2)

    # -- Collect a pending payment --
    with col1:
        st.markdown(f"#### {T.get('collect_payment', 'Collect Payment')}")
        pending_txns = get_pending_transactions(FARMER_ID)
        if not pending_txns:
            st.info(T.get("no_pending", "No pending payments."))
        else:
            for txn in pending_txns:
                with st.container():
                    st.write(f"**{txn['buyer_name']}** — ₹{txn['amount']} ({txn.get('crop', '')}, {txn.get('quantity', '')})")
                    if st.button(T.get("mark_collected", "Mark as Collected"), key=f"collect_{txn['id']}"):
                        collect_payment(txn["id"], FARMER_ID, txn["buyer_name"], txn["amount"])
                        st.success(T.get("payment_collected", "Payment collected!"))
                        st.balloons()
                        st.rerun()

    # -- Send a payment out --
    with col2:
        st.markdown(f"#### {T.get('send_payment', 'Send Payment')}")
        with st.form("send_payment_form"):
            party = st.text_input(T.get("pay_to", "Pay to"))
            amt = st.number_input(T.get("amount_label", "Amount"), min_value=0.0, step=100.0)
            submitted = st.form_submit_button(T.get("send_button", "Send"))
            if submitted:
                if not party or amt <= 0:
                    st.warning(T.get("invalid_payment", "Enter a valid name and amount."))
                else:
                    if amt > balance:
                        st.warning(T.get("low_balance_warning", "This exceeds your current wallet balance."))
                    send_payment(FARMER_ID, party, amt)
                    st.success(T.get("payment_sent", "Payment sent."))
                    st.rerun()

    # -- History --
    st.markdown(f"#### {T.get('payment_history', 'Payment History')}")
    history = get_payment_history(FARMER_ID)
    if not history:
        st.info(T.get("no_payment_history", "No payments yet."))
    else:
        for p in history:
            icon = "⬇️" if p["type"] == "collect" else "⬆️"
            date = str(p.get("created_at", ""))[:10]
            st.write(f"{icon} **{p['party_name']}** — ₹{p['amount']} ({date})")

# ---- Tab 6: Market intelligence ----
with tab6:
    st.subheader(T.get("market_subheader", "Market Prices"))

    crop = st.selectbox(T.get("select_crop", "Select crop"), ["Wheat", "Onion", "Cotton", "Mustard"])

    df, _source = get_market_prices(crop)
    # NOTE: _source is "live" or "cached" — intentionally not shown in the UI.
    # If the live API fails, it falls back to cached data silently.

    if df.empty:
        st.info(T.get("no_market_data", "No market data available for this crop yet."))
    else:
        alert = check_price_alert(crop)

        if alert["status"] == "high":
            st.success(f"📈 {crop}: ₹{alert['latest']}/quintal — {alert['pct_diff']}% {T.get('above_avg', 'above average')}")
        elif alert["status"] == "low":
            st.warning(f"📉 {crop}: ₹{alert['latest']}/quintal — {abs(alert['pct_diff'])}% {T.get('below_avg', 'below average')}")
        elif alert["status"] == "normal":
            st.info(f"{crop}: ₹{alert['latest']}/quintal — {T.get('near_avg', 'close to the recent average')}")

        # Gemini only phrases the suggestion — all numbers above are pure Python math
        advice = generate_market_advice(alert, crop, language_hint=GEMINI_LANG)
        st.markdown(f"**{T.get('suggestion_label', 'Suggestion')}:** {advice}")

        st.markdown(f"#### {T.get('mandi_comparison', 'Compare Mandis')}")
        mandi_df = compare_mandis(crop)
        if not mandi_df.empty:
            st.dataframe(mandi_df[["mandi_name", "price_per_quintal", "price_date"]], hide_index=True)

        st.markdown(f"#### {T.get('price_trend', 'Price Trend')}")
        trend_df = get_price_trend(crop, days=14)
        if not trend_df.empty:
            chart_df = trend_df.groupby("price_date")["price_per_quintal"].mean().reset_index()
            st.line_chart(chart_df.set_index("price_date"))

        st.markdown(f"#### {T.get('profit_estimator', 'Profit Estimator')}")
        col1, col2 = st.columns(2)
        with col1:
            qty = st.number_input(T.get("quantity_quintals", "Quantity (quintals)"), min_value=0.0, step=1.0)
        with col2:
            your_price = st.number_input(T.get("your_price", "Your selling price (₹/quintal)"), min_value=0.0, step=50.0)

        if qty > 0 and your_price > 0:
            result = estimate_profit(qty, alert["latest"], your_price)
            if result["better_than_market"]:
                st.success(f"{T.get('better_than_market', 'You did better than market by')} ₹{result['difference']}")
            else:
                st.warning(f"{T.get('below_market', 'You sold below market by')} ₹{abs(result['difference'])}")

# ---- Tab 7: AI Advisor (market trends + account health, narrated aloud) ----
with tab7:
    st.subheader(T.get("advisor_subheader", "🌱 Your Advisor"))
    st.caption(T.get(
        "advisor_caption",
        "Looks at crop price trends and your account, then gives one simple recommendation."
    ))

    if "advisory_text" not in st.session_state:
        st.session_state.advisory_text = None
    if "advisory_audio" not in st.session_state:
        st.session_state.advisory_audio = None

    all_crops = ["Wheat", "Onion", "Cotton", "Mustard"]
    selected_crops = st.multiselect(
        T.get("select_crops_advisor", "Which crops do you want advice on?"),
        all_crops,
        default=all_crops,
    )

    if st.button(T.get("get_advice", "Get My Advice"), key="get_advice_btn"):
        if not selected_crops:
            st.warning(T.get("pick_a_crop", "Pick at least one crop first."))
        else:
            with st.spinner(T.get("thinking", "Thinking it over...")):
                hisab_df = get_hisab(FARMER_ID)
                total_pending = float(hisab_df["Pending (₹)"].sum()) if not hisab_df.empty and "Pending (₹)" in hisab_df else 0.0
                total_paid = float(hisab_df["Paid (₹)"].sum()) if not hisab_df.empty and "Paid (₹)" in hisab_df else 0.0

                financial_data = {
                    "wallet_balance": get_wallet_balance(FARMER_ID),
                    "total_pending": total_pending,
                    "total_paid": total_paid,
                }
                # All figures above come straight from db.py / market.py math —
                # nothing here is computed or estimated by the AI model.
                market_data = get_all_crops_trend(selected_crops)

                st.session_state.advisory_text = generate_crop_advisory(
                    market_data, financial_data, language_hint=GEMINI_LANG
                )
                st.session_state.advisory_audio = None  # clear any old narration

    if st.session_state.advisory_text:
        st.markdown(f"#### {T.get('your_advice', 'Your Advice')}")
        st.write(st.session_state.advisory_text)

        if st.button(T.get("hear_advice", "🔊 Hear this out loud"), key="hear_advice_btn"):
            with st.spinner(T.get("preparing_audio", "Preparing audio...")):
                try:
                    st.session_state.advisory_audio = text_to_speech_bytes(
                        st.session_state.advisory_text, st.session_state.language
                    )
                except Exception:
                    st.error(T.get(
                        "audio_failed",
                        "Could not prepare audio right now — check your connection and try again."
                    ))

        if st.session_state.advisory_audio:
            # autoplay needs Streamlit >= 1.30; on older versions it still
            # renders a normal player, the farmer just taps play once.
            st.audio(st.session_state.advisory_audio, format="audio/mp3", autoplay=True)
