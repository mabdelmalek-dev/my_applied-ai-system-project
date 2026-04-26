from __future__ import annotations

import re
from datetime import time as _time
from typing import Any, Dict, List, Optional, Tuple

from knowledge_base import retrieve_tip

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

    tip = retrieve_tip(title)
    if tip:
        reason += f" 💡 {tip}"

    return reason


def explain_plan(schedule: List[Dict[str, Any]]) -> List[str]:
    """Return one explanation string per scheduled task."""
    return [explain_task(t) for t in schedule]


# ── Time-slotted daily scheduler ─────────────────────────────────────────────

# Preferred-time zones as (start_minute, end_minute) within the day
_ZONES = {
    "morning":   (0,       12 * 60),
    "afternoon": (12 * 60, 17 * 60),
    "evening":   (17 * 60, 24 * 60),
}


def _parse_time_str(s: str) -> _time:
    """Parse '09:00', '9:00 AM', '9:00AM' into a time object."""
    s = s.strip().upper()
    m = re.match(r"^(\d{1,2}):(\d{2})$", s)
    if m:
        return _time(int(m.group(1)), int(m.group(2)))
    m = re.match(r"^(\d{1,2}):(\d{2})\s*(AM|PM)$", s)
    if m:
        h, mn, ampm = int(m.group(1)), int(m.group(2)), m.group(3)
        if ampm == "PM" and h != 12:
            h += 12
        if ampm == "AM" and h == 12:
            h = 0
        return _time(h, mn)
    raise ValueError(f"Cannot parse time string: '{s}'")


def _t2m(t) -> int:
    """Convert a time object or 'HH:MM' string to minutes since midnight."""
    if isinstance(t, str):
        t = _parse_time_str(t)
    return t.hour * 60 + t.minute


def _m2t(m: int) -> _time:
    """Convert minutes since midnight to a time object."""
    return _time(m // 60, m % 60)


def _fmt(t: _time) -> str:
    """Format a time as '8:00 AM' / '12:30 PM'."""
    h12 = t.hour % 12 or 12
    ampm = "AM" if t.hour < 12 else "PM"
    return f"{h12}:{t.minute:02d} {ampm}"


def build_daily_schedule(
    window_start,
    window_end,
    tasks: List[Dict[str, Any]],
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Build a real time-slotted daily schedule within [window_start, window_end].

    Rules
    -----
    - Fixed-time tasks (fixed_start_time set) are locked at their specified time.
    - Flexible tasks are ranked by priority + preferred_time score, then placed
      greedily into free slots — morning-preferred tasks fill morning gaps first.
    - Tasks that cannot fit (window too small, overlap, outside window) go into
      the returned unscheduled list with a plain-English reason.

    Returns
    -------
    (scheduled, unscheduled)
    Each scheduled entry has: title, start_time, end_time, start_fmt, end_fmt,
    priority, preferred_time, fixed, duration_minutes, explanation.
    Each unscheduled entry has all original task fields plus a 'reason' key.
    """
    ws = _t2m(window_start)
    we = _t2m(window_end)
    window_label = f"{_fmt(_m2t(ws))} – {_fmt(_m2t(we))}"

    valid = validate_tasks(tasks)
    fixed_tasks = sorted(
        [t for t in valid if t.get("fixed_start_time")],
        key=lambda t: _t2m(t["fixed_start_time"]),
    )
    flexible_tasks = [t for t in valid if not t.get("fixed_start_time")]

    placed: List[Dict[str, Any]] = []   # internal: {start_min, end_min, ...}
    unscheduled: List[Dict[str, Any]] = []

    # helper: sorted list of free (start, end) minute gaps
    def _free_slots():
        occupied = sorted(placed, key=lambda x: x["start_min"])
        slots, cursor = [], ws
        for e in occupied:
            if cursor < e["start_min"]:
                slots.append((cursor, e["start_min"]))
            cursor = max(cursor, e["end_min"])
        if cursor < we:
            slots.append((cursor, we))
        return slots

    # ── Place fixed tasks ──
    for task in fixed_tasks:
        fst = _t2m(task["fixed_start_time"])
        end = fst + task["duration_minutes"]
        if fst < ws or end > we:
            unscheduled.append({**task, "reason": f"Fixed time {task['fixed_start_time']} is outside your window ({window_label})."})
            continue
        if any(not (end <= e["start_min"] or fst >= e["end_min"]) for e in placed):
            unscheduled.append({**task, "reason": f"Fixed time {task['fixed_start_time']} overlaps with another task."})
            continue
        placed.append({**task, "start_min": fst, "end_min": end, "fixed": True})

    # ── Place flexible tasks (highest score first) ──
    for task in rank_tasks(flexible_tasks):
        dur = task["duration_minutes"]
        preferred = task.get("preferred_time")
        zone = _ZONES.get(preferred) if preferred else None
        best = None

        # First pass: try preferred time zone
        if zone:
            zs, ze = zone
            for s, e in _free_slots():
                overlap_s = max(s, zs)
                overlap_e = min(e, ze)
                if overlap_e - overlap_s >= dur:
                    best = overlap_s
                    break

        # Second pass: any free slot
        if best is None:
            for s, e in _free_slots():
                if e - s >= dur:
                    best = s
                    break

        if best is not None:
            placed.append({**task, "start_min": best, "end_min": best + dur, "fixed": False})
        else:
            unscheduled.append({**task, "reason": f"Not enough free time in the window ({window_label})."})

    # ── Build final result sorted by start time ──
    placed.sort(key=lambda x: x["start_min"])
    scheduled = []
    for e in placed:
        st = _m2t(e["start_min"])
        et = _m2t(e["end_min"])
        priority = (e.get("priority") or "medium").lower()
        preferred = e.get("preferred_time")
        fixed = e.get("fixed", False)

        if fixed:
            expl = f"Fixed at {_fmt(st)} as specified by you."
        elif preferred:
            expl = (f"{e['title']} was placed at {_fmt(st)} — {priority} priority, "
                    f"prefers the {preferred}.")
        else:
            expl = f"{e['title']} was placed at {_fmt(st)} — {priority} priority."

        tip = retrieve_tip(e["title"])

        scheduled.append({
            "title": e["title"],
            "start_time": st,
            "end_time": et,
            "start_fmt": _fmt(st),
            "end_fmt": _fmt(et),
            "priority": priority,
            "preferred_time": preferred,
            "fixed": fixed,
            "duration_minutes": e["duration_minutes"],
            "explanation": expl,
            "care_tip": tip,
            "pet": e.get("pet"),
        })

    return scheduled, unscheduled


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
