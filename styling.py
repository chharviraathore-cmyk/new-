CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;600;700&family=Inter:wght@400;500&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

/* ---- App background: warm beige gradient ---- */
.stApp {
    background: linear-gradient(160deg, #FAF6EC 0%, #F1E9D8 100%);
}

/* ---- Safety net: force readable dark text everywhere ----
   Streamlit's default theme can hand out light/white text (e.g. if a
   user's system is in dark mode). Since our background is always a
   light beige, we pin body text to a dark color so nothing goes
   invisible against it. Specific elements below can still override
   this with their own color. */
.stApp, .stApp p, .stApp span, .stApp label, .stApp li,
.stMarkdown, .stMarkdown p, .stCaption,
div[data-testid="stMarkdownContainer"],
div[data-testid="stWidgetLabel"] label,
div[data-testid="stMetricLabel"],
div[data-testid="stMetricValue"],
.stTextInput label, .stNumberInput label, .stSelectbox label,
.stMultiSelect label, .stForm label {
    color: #3B3B2A !important;
}

/* Multiselect chips (crop tags in Advisor tab) */
.stMultiSelect [data-baseweb="tag"] {
    background-color: #6B7C3A !important;
}
.stMultiSelect [data-baseweb="tag"] span {
    color: #FAF6EC !important;
}

/* ---- Title ---- */
h1 {
    font-family: 'Poppins', sans-serif !important;
    color: #4A5A23 !important;
    font-weight: 700 !important;
    letter-spacing: -0.5px;
}

h2, h3 {
    font-family: 'Poppins', sans-serif !important;
    color: #556B2F !important;
}

/* ---- Tabs: pill-style, olive highlight, smooth transition ---- */
.stTabs [data-baseweb="tab-list"] {
    gap: 6px;
    background-color: #E8DCC0;
    padding: 6px;
    border-radius: 14px;
}

.stTabs [data-baseweb="tab"] {
    height: 46px;
    border-radius: 10px;
    padding: 0 18px;
    background-color: transparent;
    color: #4A4A32 !important;
    font-weight: 600;
    transition: all 0.25s ease-in-out;
}

.stTabs [data-baseweb="tab"]:hover {
    background-color: #D9C9A5;
    transform: translateY(-2px);
}

.stTabs [aria-selected="true"] {
    background-color: #6B7C3A !important;
    color: #FAF6EC !important;
    box-shadow: 0 3px 8px rgba(107, 124, 58, 0.35);
}

/* ---- Buttons: gradient olive, lift-on-hover ---- */
.stButton > button {
    background: linear-gradient(135deg, #6B7C3A 0%, #556B2F 100%);
    color: #FAF6EC;
    border: none;
    border-radius: 12px;
    padding: 0.6em 1.4em;
    font-weight: 600;
    font-family: 'Poppins', sans-serif;
    transition: all 0.2s ease-in-out;
    box-shadow: 0 2px 6px rgba(85, 107, 47, 0.25);
}

.stButton > button:hover {
    transform: translateY(-3px) scale(1.02);
    box-shadow: 0 6px 14px rgba(85, 107, 47, 0.4);
    background: linear-gradient(135deg, #7A8C46 0%, #63793A 100%);
}

.stButton > button:active {
    transform: translateY(0px) scale(0.98);
}

/* ---- Mic recorder button: pulsing glow to invite tapping ---- */
div[data-testid="stCustomComponentV1"] button {
    animation: pulse-glow 2.2s infinite;
    border-radius: 50px !important;
}

@keyframes pulse-glow {
    0%   { box-shadow: 0 0 0 0 rgba(107, 124, 58, 0.5); }
    70%  { box-shadow: 0 0 0 14px rgba(107, 124, 58, 0); }
    100% { box-shadow: 0 0 0 0 rgba(107, 124, 58, 0); }
}

/* ---- Text inputs & number inputs ---- */
.stTextInput > div > div > input,
.stNumberInput > div > div > input {
    background-color: #FFFDF7;
    border: 1.5px solid #D9C9A5;
    border-radius: 10px;
    color: #3B3B2A;
    transition: border-color 0.2s ease-in-out;
}

.stTextInput > div > div > input:focus,
.stNumberInput > div > div > input:focus {
    border-color: #6B7C3A;
    box-shadow: 0 0 0 3px rgba(107, 124, 58, 0.15);
}

/* ---- Selectbox (language picker) ---- */
.stSelectbox > div > div {
    background-color: #FFFDF7;
    border: 1.5px solid #D9C9A5;
    border-radius: 10px;
}

/* The closed box's selected-value text (e.g. "Hindi") is a separate
   element from the dropdown popup below, and needs its own color rule
   or it inherits a light/white color that vanishes on our cream bg. */
.stSelectbox div[data-baseweb="select"] {
    background-color: #FFFDF7 !important;
}
.stSelectbox div[data-baseweb="select"] * {
    color: #3B3B2A !important;
}

/* ---- Selectbox dropdown popup ----
   This list renders in a portal near the page root, NOT inside .stApp,
   and its internal markup varies across Streamlit versions. Rather than
   guess the exact nested tags, force EVERY descendant to a light bg /
   dark text so nothing can hide, regardless of internal structure. */
div[data-baseweb="popover"] {
    background-color: #FFFDF7 !important;
}

div[data-baseweb="popover"] * {
    background-color: #FFFDF7 !important;
    color: #3B3B2A !important;
}

div[data-baseweb="popover"] li:hover,
div[data-baseweb="popover"] [role="option"]:hover {
    background-color: #E8DCC0 !important;
    color: #3B3B2A !important;
}

div[data-baseweb="popover"] [aria-selected="true"] {
    background-color: #D9C9A5 !important;
    color: #3B3B2A !important;
}

/* ---- Success / error / info boxes ---- */
.stAlert {
    border-radius: 12px;
    border-left-width: 6px;
}

/* ---- Dataframe styling ---- */
[data-testid="stDataFrame"] {
    border-radius: 12px;
    overflow: hidden;
    box-shadow: 0 2px 10px rgba(85, 107, 47, 0.12);
}

/* ---- Subtle fade-in for content blocks ---- */
[data-testid="stVerticalBlock"] > div {
    animation: fadeIn 0.4s ease-in-out;
}

@keyframes fadeIn {
    from { opacity: 0; transform: translateY(6px); }
    to   { opacity: 1; transform: translateY(0); }
}
</style>
"""

# ---- Reusable HTML card for a single buyer's hisab row ----
def buyer_card_html(buyer_name, paid, pending):
    pending_color = "#9C3E28" if pending > 0 else "#4A5A23"
    return f"""
    <div style="
        background: linear-gradient(135deg, #FFFDF7 0%, #F1E9D8 100%);
        border-left: 6px solid #6B7C3A;
        border-radius: 14px;
        padding: 16px 20px;
        margin-bottom: 12px;
        box-shadow: 0 2px 10px rgba(85, 107, 47, 0.10);
        transition: transform 0.2s ease-in-out;
    ">
        <div style="font-family:'Poppins',sans-serif; font-weight:700; font-size:18px; color:#4A5A23;">
            👤 {buyer_name}
        </div>
        <div style="display:flex; gap:24px; margin-top:8px; font-family:'Inter',sans-serif;">
            <div>
                <span style="color:#5C6B3F; font-size:13px; font-weight:600;">PAID</span><br>
                <span style="font-size:20px; font-weight:600; color:#3E4E1F;">₹{paid:,.0f}</span>
            </div>
            <div>
                <span style="color:#9C4A34; font-size:13px; font-weight:600;">PENDING</span><br>
                <span style="font-size:20px; font-weight:600; color:{pending_color};">₹{pending:,.0f}</span>
            </div>
        </div>
    </div>
    """
