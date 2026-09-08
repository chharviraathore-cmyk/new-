"""
knowledge_base.py — the retrieval corpus for KisanPay's "Ask a farming question" RAG.

IMPORTANT HONESTY NOTE (read before you expand this file):
Exact sowing windows shift with state, soil, variety, and that year's rainfall.
Entries below are GENERAL India-wide windows commonly cited by agricultural
extension sources — they are a starting point, not a substitute for your local
Krishi Vigyan Kendra (KVK) or state agriculture department's advisory for your
exact district. rag.py's prompt explicitly tells the model to say this to the
farmer for any sowing-timing question, on top of these notes.

Each entry: a short id, the plain-language fact, and tags used only for your own
bookkeeping (not used in retrieval — retrieval is purely by meaning/embedding).

TODO before real deployment: have an actual agronomist or your state's
Department of Agriculture review and replace/expand these entries. This file
is a demo-quality starting corpus, not verified agricultural guidance.
"""

KNOWLEDGE_BASE = [
    {
        "id": "wheat_sowing",
        "crop": "wheat",
        "text": (
            "Wheat is a Rabi (winter) crop in most of North India. The commonly "
            "recommended sowing window is mid-October to mid-November. Sowing "
            "after late November ('late sowing') generally reduces yield because "
            "the crop then flowers during hotter weather."
        ),
    },
    {
        "id": "wheat_harvest",
        "crop": "wheat",
        "text": (
            "Wheat sown on time (mid-Oct to mid-Nov) is typically ready for harvest "
            "around March to April, roughly 120-150 days after sowing depending on "
            "the variety."
        ),
    },
    {
        "id": "mustard_sowing",
        "crop": "mustard",
        "text": (
            "Mustard is a Rabi crop, generally sown from early October to early "
            "November, similar to wheat's window but often slightly earlier. It's "
            "commonly grown alongside or as a border crop to wheat in North India."
        ),
    },
    {
        "id": "onion_sowing",
        "crop": "onion",
        "text": (
            "Onion sowing in India isn't a single window — there are typically "
            "three possible seasons depending on the region: Kharif (June-July "
            "sowing), late Kharif (Oct-Nov sowing), and Rabi (Oct-Dec nursery, "
            "transplanted Dec-Jan). Which season is used depends heavily on local "
            "practice and irrigation access."
        ),
    },
    {
        "id": "cotton_sowing",
        "crop": "cotton",
        "text": (
            "Cotton is mainly a Kharif (monsoon) crop. Irrigated cotton is often "
            "sown April-May; rain-fed cotton is typically sown after the monsoon "
            "arrives, around June. Harvest generally runs October through January."
        ),
    },
    {
        "id": "rabi_season_general",
        "crop": "general",
        "text": (
            "The Rabi season in India runs roughly October to March — crops are "
            "sown after the monsoon retreats and harvested in spring. Wheat and "
            "mustard are the two most common Rabi crops in North India."
        ),
    },
    {
        "id": "kharif_season_general",
        "crop": "general",
        "text": (
            "The Kharif season in India runs roughly June to October, sown with "
            "the arrival of the monsoon and harvested in autumn. Cotton and many "
            "onion varieties fall in this season."
        ),
    },
    {
        "id": "quintal_definition",
        "crop": "units",
        "text": (
            "A quintal is a standard unit of weight equal to 100 kilograms. It is "
            "the standard unit most Indian mandi price boards use, including the "
            "prices shown in KisanPay's Market tab."
        ),
    },
    {
        "id": "bori_katta_definition",
        "crop": "units",
        "text": (
            "'Bori' and 'katta' are informal, colloquial words for a sack or bag "
            "of produce, commonly used in everyday farmer conversation. Unlike a "
            "quintal, they are NOT a fixed standard weight — a bori's actual "
            "weight varies by crop, region, and even the specific trader, so it "
            "should always be confirmed by actual weighing, not assumed."
        ),
    },
    {
        "id": "mandi_definition",
        "crop": "general",
        "text": (
            "A mandi is a regulated wholesale market (often an APMC - Agricultural "
            "Produce Market Committee - yard) where farmers sell crops to traders "
            "or buyers, and prices are typically recorded and published daily."
        ),
    },
    {
        "id": "price_trend_explainer",
        "crop": "general",
        "text": (
            "When a crop's latest price is noticeably higher than its recent "
            "average, it often signals stronger demand or lower supply that week "
            "— though prices can reverse quickly, so it's not a guarantee of a "
            "continuing trend."
        ),
    },
    {
        "id": "sowing_timing_caveat",
        "crop": "general",
        "text": (
            "Exact sowing dates for any crop shift based on local rainfall, soil "
            "moisture, seed variety, and elevation — general national windows are "
            "a starting reference point only. Farmers should confirm exact local "
            "timing with their nearest Krishi Vigyan Kendra (KVK) or state "
            "agriculture department advisory."
        ),
    },
]
