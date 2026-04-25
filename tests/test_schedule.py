"""
Tests for build_daily_schedule — the time-slotted daily planner.

Covers: fixed tasks, flexible placement, priority ordering, preferred-time
zones, overlap prevention, out-of-window rejection, and edge cases.
"""

from datetime import time
from agent import build_daily_schedule


# ── Fixed-time tasks ──────────────────────────────────────────────────────────

def test_fixed_task_placed_at_exact_time():
    tasks = [{"title": "Medicine", "duration_minutes": 5, "priority": "high",
              "fixed_start_time": "09:00"}]
    scheduled, unscheduled = build_daily_schedule(time(8, 0), time(12, 0), tasks)
    assert len(scheduled) == 1
    assert scheduled[0]["start_fmt"] == "9:00 AM"
    assert scheduled[0]["fixed"] is True


def test_fixed_task_outside_window_goes_to_unscheduled():
    tasks = [{"title": "Night walk", "duration_minutes": 10, "priority": "high",
              "fixed_start_time": "22:00"}]
    scheduled, unscheduled = build_daily_schedule(time(8, 0), time(12, 0), tasks)
    assert len(scheduled) == 0
    assert len(unscheduled) == 1
    assert "outside" in unscheduled[0]["reason"].lower()


def test_two_overlapping_fixed_tasks_second_is_rejected():
    tasks = [
        {"title": "Task A", "duration_minutes": 30, "priority": "high",  "fixed_start_time": "09:00"},
        {"title": "Task B", "duration_minutes": 20, "priority": "medium", "fixed_start_time": "09:15"},
    ]
    scheduled, unscheduled = build_daily_schedule(time(8, 0), time(12, 0), tasks)
    titles = [e["title"] for e in scheduled]
    assert "Task A" in titles
    assert "Task B" not in titles
    assert any("overlap" in u["reason"].lower() for u in unscheduled)


# ── Flexible tasks ────────────────────────────────────────────────────────────

def test_high_priority_task_scheduled_first():
    tasks = [
        {"title": "Low task",  "duration_minutes": 10, "priority": "low"},
        {"title": "High task", "duration_minutes": 10, "priority": "high"},
    ]
    scheduled, _ = build_daily_schedule(time(8, 0), time(12, 0), tasks)
    assert scheduled[0]["title"] == "High task"


def test_tasks_do_not_overlap():
    tasks = [
        {"title": "Task A", "duration_minutes": 30, "priority": "high"},
        {"title": "Task B", "duration_minutes": 30, "priority": "medium"},
        {"title": "Task C", "duration_minutes": 30, "priority": "low"},
    ]
    scheduled, _ = build_daily_schedule(time(8, 0), time(12, 0), tasks)
    for i in range(len(scheduled) - 1):
        a, b = scheduled[i], scheduled[i + 1]
        assert a["end_time"] <= b["start_time"], (
            f"{a['title']} ends {a['end_fmt']} but {b['title']} starts {b['start_fmt']}"
        )


def test_task_too_long_for_window_is_unscheduled():
    tasks = [{"title": "Long task", "duration_minutes": 300, "priority": "high"}]
    scheduled, unscheduled = build_daily_schedule(time(8, 0), time(9, 0), tasks)
    assert len(scheduled) == 0
    assert len(unscheduled) == 1


def test_all_tasks_fit_when_window_is_large():
    tasks = [
        {"title": "Walk",     "duration_minutes": 30, "priority": "high"},
        {"title": "Feed",     "duration_minutes": 10, "priority": "medium"},
        {"title": "Medicine", "duration_minutes": 5,  "priority": "high"},
    ]
    scheduled, unscheduled = build_daily_schedule(time(8, 0), time(18, 0), tasks)
    assert len(unscheduled) == 0
    assert len(scheduled) == 3


# ── Preferred time ────────────────────────────────────────────────────────────

def test_morning_preferred_task_placed_before_noon():
    tasks = [{"title": "Morning walk", "duration_minutes": 30, "priority": "medium",
              "preferred_time": "morning"}]
    scheduled, _ = build_daily_schedule(time(8, 0), time(18, 0), tasks)
    assert len(scheduled) == 1
    assert scheduled[0]["start_time"].hour < 12


def test_afternoon_preferred_task_placed_after_noon():
    tasks = [{"title": "Afternoon play", "duration_minutes": 20, "priority": "medium",
              "preferred_time": "afternoon"}]
    scheduled, _ = build_daily_schedule(time(8, 0), time(18, 0), tasks)
    assert len(scheduled) == 1
    assert scheduled[0]["start_time"].hour >= 12


def test_preferred_time_respected_when_slot_available():
    # morning task should land before noon even though other tasks are also present
    tasks = [
        {"title": "Evening task", "duration_minutes": 30, "priority": "medium",
         "preferred_time": "evening"},
        {"title": "Morning task", "duration_minutes": 30, "priority": "medium",
         "preferred_time": "morning"},
    ]
    scheduled, _ = build_daily_schedule(time(8, 0), time(22, 0), tasks)
    by_title = {e["title"]: e for e in scheduled}
    assert by_title["Morning task"]["start_time"].hour < 12
    assert by_title["Evening task"]["start_time"].hour >= 17


# ── Mixed fixed + flexible ────────────────────────────────────────────────────

def test_fixed_and_flexible_tasks_combined():
    """Reproduces the spec example: medicine at 9:00, walk/play/brush flexible."""
    tasks = [
        {"title": "Give medicine", "duration_minutes": 5,  "priority": "high",
         "fixed_start_time": "09:00"},
        {"title": "Walk dog",      "duration_minutes": 30, "priority": "high",
         "preferred_time": "morning"},
        {"title": "Brush fur",     "duration_minutes": 15, "priority": "low"},
        {"title": "Play time",     "duration_minutes": 20, "priority": "medium"},
    ]
    scheduled, unscheduled = build_daily_schedule(time(8, 0), time(11, 0), tasks)
    titles = [e["title"] for e in scheduled]
    assert "Give medicine" in titles
    assert "Walk dog" in titles
    # medicine must be at exactly 9:00 AM
    med = next(e for e in scheduled if e["title"] == "Give medicine")
    assert med["start_fmt"] == "9:00 AM"
    # no overlaps
    for i in range(len(scheduled) - 1):
        assert scheduled[i]["end_time"] <= scheduled[i + 1]["start_time"]


# ── Edge cases ────────────────────────────────────────────────────────────────

def test_empty_task_list_returns_empty_schedule():
    scheduled, unscheduled = build_daily_schedule(time(8, 0), time(12, 0), [])
    assert scheduled == []
    assert unscheduled == []


def test_explanation_included_in_every_scheduled_entry():
    tasks = [{"title": "Feed cat", "duration_minutes": 10, "priority": "medium"}]
    scheduled, _ = build_daily_schedule(time(8, 0), time(12, 0), tasks)
    assert all("explanation" in e for e in scheduled)
    assert all(e["explanation"] for e in scheduled)
