"""
PawPal+ Knowledge Base — Retrieval-Augmented Generation (RAG) module
=====================================================================
A lightweight local knowledge base of pet care facts.
retrieve_tip(task_title) returns the most relevant care tip for a task
by scoring keyword overlap between the query and each indexed entry.
"""

from __future__ import annotations
import re
from typing import Optional

# ── Knowledge base: list of (keywords, tip) pairs ─────────────────────────────
_KB: list[tuple[list[str], str]] = [
    (
        ["walk", "walking", "exercise", "stroll", "outdoor"],
        "Dogs need at least 30 minutes of exercise daily to maintain healthy weight and mental stimulation.",
    ),
    (
        ["feed", "feeding", "meal", "food", "breakfast", "dinner", "lunch"],
        "Feed pets at consistent times each day — regular mealtimes reduce anxiety and support digestion.",
    ),
    (
        ["water", "hydration", "drink", "fresh water"],
        "Fresh water should be available at all times; refill the bowl at least twice a day.",
    ),
    (
        ["medicine", "medication", "pill", "tablet", "dose", "drug", "supplement", "vitamin"],
        "Always give medication at the same time each day to maintain steady therapeutic levels in the bloodstream.",
    ),
    (
        ["groom", "grooming", "brush", "brushing", "fur", "coat", "shed"],
        "Regular brushing removes loose fur, prevents matting, and distributes natural skin oils.",
    ),
    (
        ["bath", "bathe", "bathing", "wash", "shampoo"],
        "Most dogs need a bath every 4–6 weeks; bathing too often strips protective oils from the coat.",
    ),
    (
        ["play", "playtime", "game", "toy", "fetch", "tug"],
        "Interactive play strengthens the pet-owner bond and provides essential cognitive enrichment.",
    ),
    (
        ["train", "training", "obedience", "command", "trick", "sit", "stay"],
        "Short, positive-reinforcement sessions (5–10 min) are more effective than long drills.",
    ),
    (
        ["vet", "veterinarian", "checkup", "check-up", "appointment", "clinic"],
        "Annual wellness exams catch health issues early — prevention is far less costly than treatment.",
    ),
    (
        ["nail", "nails", "claw", "claws", "trim", "clipping"],
        "Trim nails every 3–4 weeks; overgrown nails can cause joint pain and affect gait.",
    ),
    (
        ["dental", "teeth", "tooth", "brush teeth", "oral"],
        "Daily teeth brushing (or dental chews) prevents periodontal disease, which affects 80% of dogs over age 3.",
    ),
    (
        ["socialize", "socialization", "play date", "dog park", "meet"],
        "Early and ongoing socialization reduces fear and aggression in unfamiliar situations.",
    ),
    (
        ["rest", "sleep", "nap", "relax", "quiet"],
        "Adult dogs sleep 12–14 hours a day; ensure a quiet, comfortable resting area is always available.",
    ),
    (
        ["litter", "litter box", "clean", "scoop"],
        "Scoop litter boxes at least once a day — cats will avoid a dirty box, which can cause stress-related issues.",
    ),
    (
        ["cat", "kitten", "feline"],
        "Cats are crepuscular (most active at dawn and dusk); schedule interactive play around those windows for best engagement.",
    ),
    (
        ["bird", "parrot", "avian", "cage"],
        "Birds need at least 2–4 hours outside the cage daily for mental health and physical exercise.",
    ),
    (
        ["rabbit", "bunny", "hay"],
        "Rabbits should have unlimited timothy hay, which keeps their continuously growing teeth worn down.",
    ),
]


def _tokenize(text: str) -> set[str]:
    """Lowercase and split into words, stripping punctuation."""
    return set(re.findall(r"[a-z]+", text.lower()))


def retrieve_tip(task_title: str) -> Optional[str]:
    """
    Return the most relevant pet care tip for *task_title*, or None if
    no entry scores above the minimum threshold.

    Scoring: number of keyword tokens shared between the query and an
    entry's keyword list.  Threshold: at least 1 match required.
    """
    query_tokens = _tokenize(task_title)
    best_score, best_tip = 0, None

    for keywords, tip in _KB:
        score = len(query_tokens & set(keywords))
        if score > best_score:
            best_score = score
            best_tip = tip

    return best_tip if best_score >= 1 else None
