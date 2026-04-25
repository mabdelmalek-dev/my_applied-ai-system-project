"""
Tests for the PawPal+ agentic planner.

Each test verifies one decision the planner must make correctly:
- priority ordering
- available time limits
- preferred_time scoring
- explanation content
- edge cases
"""

from agent import (
    build_daily_plan,
    validate_tasks,
    rank_tasks,
    schedule_tasks,
    score_task,
    explain_task,
    explain_plan,
)


# ── build_daily_plan (end-to-end) ─────────────────────────────────────────────

def test_high_priority_task_comes_first():
    tasks = [
        {"title": "Brush fur", "duration_minutes": 10, "priority": "low"},
        {"title": "Give medicine", "duration_minutes": 5, "priority": "high"},
    ]
    plan, explanations = build_daily_plan(None, None, tasks, 30)
    assert plan[0]["title"] == "Give medicine"


def test_all_tasks_scheduled_when_time_is_sufficient():
    tasks = [
        {"title": "Feed breakfast", "duration_minutes": 10, "priority": "high"},
        {"title": "Morning walk", "duration_minutes": 30, "priority": "medium"},
        {"title": "Brush fur", "duration_minutes": 10, "priority": "low"},
    ]
    plan, _ = build_daily_plan(None, None, tasks, 60)
    assert len(plan) == 3


def test_low_priority_task_dropped_when_time_is_tight():
    tasks = [
        {"title": "Give medicine", "duration_minutes": 5, "priority": "high"},
        {"title": "Play fetch", "duration_minutes": 45, "priority": "low"},
    ]
    # only 20 minutes available — Play fetch (45 min) should be dropped
    plan, _ = build_daily_plan(None, None, tasks, 20)
    titles = [t["title"] for t in plan]
    assert "Give medicine" in titles
    assert "Play fetch" not in titles


def test_explanations_match_schedule_length():
    tasks = [
        {"title": "Feed", "duration_minutes": 10, "priority": "high"},
        {"title": "Walk", "duration_minutes": 20, "priority": "medium"},
    ]
    plan, explanations = build_daily_plan(None, None, tasks, 60)
    assert len(explanations) == len(plan)


# ── validate_tasks ────────────────────────────────────────────────────────────

def test_validate_removes_task_with_no_title():
    tasks = [
        {"title": "", "duration_minutes": 10, "priority": "high"},
        {"title": "Walk", "duration_minutes": 20, "priority": "medium"},
    ]
    valid = validate_tasks(tasks)
    assert len(valid) == 1
    assert valid[0]["title"] == "Walk"


def test_validate_removes_task_with_zero_duration():
    tasks = [
        {"title": "Feed", "duration_minutes": 0, "priority": "high"},
        {"title": "Walk", "duration_minutes": 15, "priority": "medium"},
    ]
    valid = validate_tasks(tasks)
    assert len(valid) == 1
    assert valid[0]["title"] == "Walk"


def test_validate_accepts_all_valid_tasks():
    tasks = [
        {"title": "Walk", "duration_minutes": 20, "priority": "high"},
        {"title": "Feed", "duration_minutes": 10, "priority": "medium"},
    ]
    assert len(validate_tasks(tasks)) == 2


# ── score_task ────────────────────────────────────────────────────────────────

def test_high_priority_scores_higher_than_medium():
    high = score_task({"title": "t", "duration_minutes": 10, "priority": "high"})
    medium = score_task({"title": "t", "duration_minutes": 10, "priority": "medium"})
    assert high > medium


def test_medium_priority_scores_higher_than_low():
    medium = score_task({"title": "t", "duration_minutes": 10, "priority": "medium"})
    low = score_task({"title": "t", "duration_minutes": 10, "priority": "low"})
    assert medium > low


def test_preferred_time_adds_bonus_to_score():
    without = score_task({"title": "t", "duration_minutes": 10, "priority": "medium"})
    with_pt = score_task({"title": "t", "duration_minutes": 10, "priority": "medium", "preferred_time": "morning"})
    assert with_pt > without


# ── rank_tasks ────────────────────────────────────────────────────────────────

def test_rank_tasks_orders_high_before_low():
    tasks = [
        {"title": "Low", "duration_minutes": 10, "priority": "low"},
        {"title": "High", "duration_minutes": 10, "priority": "high"},
        {"title": "Medium", "duration_minutes": 10, "priority": "medium"},
    ]
    ranked = rank_tasks(tasks)
    assert ranked[0]["title"] == "High"
    assert ranked[-1]["title"] == "Low"


def test_rank_tasks_attaches_score():
    tasks = [{"title": "Walk", "duration_minutes": 20, "priority": "high"}]
    ranked = rank_tasks(tasks)
    assert "_score" in ranked[0]


# ── schedule_tasks ────────────────────────────────────────────────────────────

def test_schedule_respects_available_minutes():
    ranked = [
        {"title": "A", "duration_minutes": 30, "_score": 100, "priority": "high"},
        {"title": "B", "duration_minutes": 30, "_score": 50, "priority": "medium"},
        {"title": "C", "duration_minutes": 30, "_score": 10, "priority": "low"},
    ]
    scheduled = schedule_tasks(ranked, 60)
    total = sum(t["duration_minutes"] for t in scheduled)
    assert total <= 60


def test_schedule_skips_task_too_long_for_remaining_time():
    ranked = [
        {"title": "Short", "duration_minutes": 10, "_score": 100, "priority": "high"},
        {"title": "Too long", "duration_minutes": 100, "_score": 50, "priority": "medium"},
    ]
    scheduled = schedule_tasks(ranked, 30)
    titles = [t["title"] for t in scheduled]
    assert "Short" in titles
    assert "Too long" not in titles


# ── explain_task ──────────────────────────────────────────────────────────────

def test_explain_task_mentions_priority():
    task = {"title": "Walk dog", "duration_minutes": 30, "priority": "high"}
    explanation = explain_task(task)
    assert "high" in explanation.lower()


def test_explain_task_mentions_duration():
    task = {"title": "Walk dog", "duration_minutes": 30, "priority": "high"}
    explanation = explain_task(task)
    assert "30" in explanation


def test_explain_task_mentions_preferred_time_when_set():
    task = {"title": "Walk dog", "duration_minutes": 30, "priority": "high", "preferred_time": "morning"}
    explanation = explain_task(task)
    assert "morning" in explanation.lower()


def test_explain_task_no_preferred_time_mention_when_absent():
    task = {"title": "Feed cat", "duration_minutes": 10, "priority": "medium"}
    explanation = explain_task(task)
    assert "morning" not in explanation
    assert "afternoon" not in explanation
    assert "evening" not in explanation


def test_explain_plan_returns_one_entry_per_task():
    scheduled = [
        {"title": "Walk", "duration_minutes": 30, "priority": "high"},
        {"title": "Feed", "duration_minutes": 10, "priority": "medium"},
    ]
    explanations = explain_plan(scheduled)
    assert len(explanations) == 2
