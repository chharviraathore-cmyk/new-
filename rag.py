"""
rag.py — Retrieval-Augmented Generation for KisanPay's "Ask a farming question" feature.

WHY THIS EXISTS: the old "Ask" tab fed whatever the farmer typed straight into a
generic "explain this in words" prompt meant for buyer-due amounts. If someone typed
a real farming question in there, the AI had nothing real to ground itself on and
would produce a plausible-sounding but made-up answer. That's the exact failure
mode RAG is meant to prevent: retrieve real facts FIRST, then only let the AI phrase
what was actually retrieved — never let it answer from pure guesswork.

HOW IT WORKS:
1. Every fact in knowledge_base.py is converted into an embedding (a vector of
   numbers capturing its meaning) using Gemini's embedding model, once, and cached
   to disk in kb_cache.json so we don't re-embed on every app restart.
2. When a farmer asks a question, we embed the QUESTION the same way, and compare
   it against every cached fact using cosine similarity (a standard way to measure
   how close two meaning-vectors are).
3. The top few matching facts are handed to Gemini with a strict instruction:
   answer ONLY using these facts. If nothing matches well enough, we say so honestly
   instead of letting the model fill the gap with invented advice.

FALLBACK: if the embedding API is unavailable (quota, network), retrieval falls
back to simple keyword overlap instead of failing outright — lower quality
matching, but the app keeps working and still never lets the AI answer ungrounded.
"""

import os
import json
import math
from ai import model  # reuse the already-configured Gemini model from ai.py
import google.generativeai as genai
from knowledge_base import KNOWLEDGE_BASE

EMBED_MODEL = "models/text-embedding-004"
CACHE_PATH = os.path.join(os.path.dirname(__file__), "kb_cache.json")


def _embed(text: str, task_type: str) -> list:
    """Returns an embedding vector for `text`, or raises on API failure."""
    result = genai.embed_content(model=EMBED_MODEL, content=text, task_type=task_type)
    return result["embedding"]


def _cosine_similarity(a: list, b: list) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def _build_index():
    """Embeds every knowledge base entry and caches the result to disk.
    Only re-runs if the knowledge base has changed since the last cache."""
    kb_signature = str(len(KNOWLEDGE_BASE)) + "".join(e["id"] for e in KNOWLEDGE_BASE)

    if os.path.exists(CACHE_PATH):
        with open(CACHE_PATH, "r", encoding="utf-8") as f:
            cached = json.load(f)
        if cached.get("signature") == kb_signature:
            return cached["entries"]

    entries = []
    for entry in KNOWLEDGE_BASE:
        embedding = _embed(entry["text"], task_type="retrieval_document")
        entries.append({**entry, "embedding": embedding})

    with open(CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump({"signature": kb_signature, "entries": entries}, f)

    return entries


def _keyword_fallback_retrieve(query: str, top_k: int):
    """Used only if embeddings are unavailable. Crude but honest: scores each
    entry by how many query words it shares, so the app degrades instead of
    crashing or (worse) answering ungrounded."""
    query_words = set(query.lower().split())
    scored = []
    for entry in KNOWLEDGE_BASE:
        entry_words = set(entry["text"].lower().split())
        overlap = len(query_words & entry_words)
        score = overlap / max(len(query_words), 1)
        scored.append({**entry, "score": score})
    scored.sort(key=lambda e: e["score"], reverse=True)
    return scored[:top_k]


def retrieve(query: str, top_k: int = 3):
    """Returns the top_k most relevant knowledge base entries for `query`,
    each with a similarity "score" between 0 and 1."""
    try:
        indexed_entries = _build_index()
        query_embedding = _embed(query, task_type="retrieval_query")
        scored = [
            {**entry, "score": _cosine_similarity(query_embedding, entry["embedding"])}
            for entry in indexed_entries
        ]
        for entry in scored:
            entry.pop("embedding", None)
        scored.sort(key=lambda e: e["score"], reverse=True)
        return scored[:top_k]
    except Exception:
        # Embedding API unavailable (quota/network) — degrade, don't crash.
        return _keyword_fallback_retrieve(query, top_k)


def _no_answer_message(language_hint: str) -> str:
    prompt = (
        f"In {language_hint} only, write one short, honest sentence telling a farmer "
        f"you don't have verified information to answer their question, and that they "
        f"should ask their nearest Krishi Vigyan Kendra or local agriculture office. "
        f"Under 25 words, no English words mixed in."
    )
    response = model.generate_content(prompt)
    return response.text.strip()


def answer_farming_question(query: str, language_hint: str = "Hindi", top_k: int = 3, min_similarity: float = 0.35) -> str:
    """
    The main entry point. Retrieves relevant facts, then asks Gemini to phrase
    an answer using ONLY those facts. Returns an honest "I don't know" message
    (still AI-phrased, but grounded in nothing invented) if nothing relevant
    was found — this is the safeguard against the old bug's hallucinated answers.
    """
    passages = retrieve(query, top_k=top_k)

    if not passages or passages[0]["score"] < min_similarity:
        return _no_answer_message(language_hint)

    context = "\n".join(f"- {p['text']}" for p in passages)

    prompt = f"""
You are answering an Indian farmer's question, in {language_hint} only. Use ONLY the
facts listed below — do not invent any date, number, or piece of advice that isn't
in these facts. If the facts don't fully answer the question, say plainly that you
don't have complete information, rather than guessing.

FACTS:
{context}

FARMER'S QUESTION: {query}

Write a short, plain-spoken answer (under 80 words, {language_hint} only, no English
words mixed in). If the question is about sowing or harvest timing, remind them that
exact local dates can shift with rainfall and soil, and that they should confirm with
their nearest Krishi Vigyan Kendra (KVK) for their exact area.
"""
    response = model.generate_content(prompt)
    return response.text.strip()


if __name__ == "__main__":
    # Quick manual test: run `python rag.py` (needs GEMINI_API_KEY set)
    print(answer_farming_question("when to sow wheat like the exact time", language_hint="English"))
    print(answer_farming_question("what is the capital of France", language_hint="English"))  # should say "don't know"
