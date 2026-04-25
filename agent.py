from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

# ── Scoring constants ──────────────────────────────────────────────────────────
_PRIORITY_SCORE = {"high": 100, "medium": 50, "low": 10}
_PREFERRED_TIME_BONUS = 10   # bonus when a preferred_time is specified


# ── Step 1: validate ──────────────────────────────────────────────────────────

def validate_tasks(tasks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Return only tasks that have a non-empty title and positive duration."""
    valid = []
    for t in tasks:
        title = (t.get("title") or t.get("name", "")).strip()
        duration = int(t.get("duration_minutes") or t.get("duration") or 0)
        if title and duration > 0:
            # normalise key names so the rest of the pipeline is consistent
            valid.append({**t, "title": title, "duration_minutes": duration})
    return valid


# ── Step 2: rank ──────────────────────────────────────────────────────────────

def score_task(task: Dict[str, Any]) -> int:
    """
    Score a task based on its AI decision factors.

    Priority contributes the base score; having a preferred_time adds a bonus
    because the owner cares enough about timing to specify one.
    """
    score = _PRIORITY_SCORE.get((task.get("priority") or "low").lower(), 10)
    if task.get("preferred_time") in ("morning", "afternoon", "evening"):
        score += _PREFERRED_TIME_BONUS
    return score


def rank_tasks(
    tasks: List[Dict[str, Any]],
    owner=None,
    pet=None,
) -> List[Dict[str, Any]]:
    """
    Rank tasks from highest to lowest score.

    Each returned task dict gets a '_score' key so callers can display it.
    """
    scored = [{**t, "_score": score_task(t)} for t in tasks]
    scored.sort(key=lambda x: -x["_score"])
    return scored


# ── Step 3: schedule ──────────────────────────────────────────────────────────

def schedule_tasks(
    ranked_tasks: List[Dict[str, Any]],
    available_minutes: int,
) -> List[Dict[str, Any]]:
    """
    Greedily fit tasks into the available time budget.

    Tasks are already sorted by score (highest first), so the most important
    tasks are placed before lower-priority ones.  A task is skipped only when
    it would exceed the remaining time.
    """
    remaining = available_minutes
    scheduled = []
    for task in ranked_tasks:
        duration = task["duration_minutes"]
        if duration <= remaining:
            scheduled.append(task)
            remaining -= duration
    return scheduled


# ── Step 4: explain ───────────────────────────────────────────────────────────

def explain_task(task: Dict[str, Any]) -> str:
    """Return a natural-language sentence explaining why a task was scheduled."""
    title = task.get("title") or task.get("name", "This task")
    priority = (task.get("priority") or "medium").lower()
    duration = task.get("duration_minutes") or task.get("duration", "?")
    preferred = task.get("preferred_time")

    reason = (
        f"{title} was chosen because it has {priority} priority "
        f"and takes {duration} minutes."
    )
    if preferred:
        reason += f" It is preferred in the {preferred}."
    return reason


def explain_plan(schedule: List[Dict[str, Any]]) -> List[str]:
    """Return one explanation string per scheduled task."""
    return [explain_task(t) for t in schedule]


# ── Main entry-point ──────────────────────────────────────────────────────────

def build_daily_plan(
    owner,
    pet,
    tasks: List[Dict[str, Any]],
    available_minutes: int,
) -> Tuple[List[Dict[str, Any]], List[str]]:
    """
    Agentic workflow — four explicit steps:

      1. validate_tasks  — drop tasks with missing title or zero duration
      2. rank_tasks      — score by priority + preferred_time, sort high→low
      3. schedule_tasks  — greedy fit within available_minutes
      4. explain_plan    — generate a natural-language reason per task

    Returns (schedule, explanations).
    """
    valid_tasks = validate_tasks(tasks)
    ranked_tasks = rank_tasks(valid_tasks, owner, pet)
    schedule = schedule_tasks(ranked_tasks, available_minutes)
    explanations = explain_plan(schedule)
    return schedule, explanations
