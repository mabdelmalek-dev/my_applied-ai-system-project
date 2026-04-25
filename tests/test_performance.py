"""
Performance / reliability tests for the PawPal+ AI planner.

These tests verify that the planner meets measurable quality thresholds:
  - task_coverage  >= expected value
  - priority_compliance == 1.0 when it should be
  - time_efficiency within expected range
  - overall_score above minimum threshold
  - all benchmark scenarios pass
"""

from metrics import (
    evaluate_plan,
    task_coverage,
    time_efficiency,
    priority_compliance,
    run_benchmarks,
)
from agent import build_daily_plan


# ── task_coverage ─────────────────────────────────────────────────────────────

def test_coverage_is_1_when_all_tasks_fit():
    tasks = [
        {"title": "Walk",  "duration_minutes": 20, "priority": "high"},
        {"title": "Feed",  "duration_minutes": 10, "priority": "medium"},
        {"title": "Brush", "duration_minutes": 10, "priority": "low"},
    ]
    schedule, _ = build_daily_plan(None, None, tasks, 120)
    assert task_coverage(tasks, schedule) == 1.0


def test_coverage_is_less_than_1_when_some_tasks_skipped():
    tasks = [
        {"title": "Quick task", "duration_minutes": 5,  "priority": "high"},
        {"title": "Long task",  "duration_minutes": 200, "priority": "low"},
    ]
    schedule, _ = build_daily_plan(None, None, tasks, 30)
    assert task_coverage(tasks, schedule) < 1.0


def test_coverage_is_1_for_empty_task_list():
    assert task_coverage([], []) == 1.0


# ── time_efficiency ───────────────────────────────────────────────────────────

def test_efficiency_is_1_when_time_fully_used():
    tasks = [{"title": "Fill time", "duration_minutes": 60, "priority": "high"}]
    schedule, _ = build_daily_plan(None, None, tasks, 60)
    assert time_efficiency(schedule, 60) == 1.0


def test_efficiency_is_0_for_empty_schedule():
    assert time_efficiency([], 60) == 0.0


def test_efficiency_never_exceeds_1():
    tasks = [{"title": "Task", "duration_minutes": 10, "priority": "high"}]
    schedule, _ = build_daily_plan(None, None, tasks, 5)
    assert time_efficiency(schedule, 5) <= 1.0


# ── priority_compliance ───────────────────────────────────────────────────────

def test_compliance_is_1_when_high_priority_scheduled():
    tasks = [
        {"title": "High",   "duration_minutes": 10, "priority": "high"},
        {"title": "Medium", "duration_minutes": 10, "priority": "medium"},
    ]
    schedule, _ = build_daily_plan(None, None, tasks, 60)
    assert priority_compliance(tasks, schedule) == 1.0


def test_compliance_is_1_when_all_tasks_scheduled():
    tasks = [
        {"title": "A", "duration_minutes": 10, "priority": "high"},
        {"title": "B", "duration_minutes": 10, "priority": "low"},
    ]
    schedule, _ = build_daily_plan(None, None, tasks, 60)
    assert priority_compliance(tasks, schedule) == 1.0


def test_compliance_is_1_when_high_priority_wins_tie():
    # Both tasks same duration, only one fits — planner must pick high over low
    tasks = [
        {"title": "High task", "duration_minutes": 10, "priority": "high"},
        {"title": "Low task",  "duration_minutes": 10, "priority": "low"},
    ]
    schedule, _ = build_daily_plan(None, None, tasks, 10)
    # planner should schedule the high-priority one
    assert any(t["title"] == "High task" for t in schedule)
    assert priority_compliance(tasks, schedule) == 1.0


def test_compliance_is_1_for_empty_schedule():
    assert priority_compliance([], []) == 1.0


# ── evaluate_plan (combined) ──────────────────────────────────────────────────

def test_evaluate_plan_returns_all_keys():
    tasks = [{"title": "Walk", "duration_minutes": 20, "priority": "high"}]
    schedule, _ = build_daily_plan(None, None, tasks, 60)
    result = evaluate_plan(tasks, schedule, 60)
    assert set(result.keys()) == {"task_coverage", "time_efficiency", "priority_compliance", "overall_score"}


def test_evaluate_plan_all_scores_between_0_and_1():
    tasks = [
        {"title": "Feed", "duration_minutes": 10, "priority": "high"},
        {"title": "Walk", "duration_minutes": 30, "priority": "medium"},
        {"title": "Play", "duration_minutes": 60, "priority": "low"},
    ]
    schedule, _ = build_daily_plan(None, None, tasks, 60)
    result = evaluate_plan(tasks, schedule, 60)
    for key, value in result.items():
        assert 0.0 <= value <= 1.0, f"{key} = {value} is out of range"


def test_evaluate_plan_overall_score_above_minimum_threshold():
    tasks = [
        {"title": "Give medicine", "duration_minutes": 5,  "priority": "high"},
        {"title": "Morning walk",  "duration_minutes": 30, "priority": "medium"},
        {"title": "Brush fur",     "duration_minutes": 10, "priority": "low"},
    ]
    # available_minutes matches total task duration so time_efficiency is high
    schedule, _ = build_daily_plan(None, None, tasks, 50)
    result = evaluate_plan(tasks, schedule, 50)
    assert result["overall_score"] >= 0.8, (
        f"Overall score {result['overall_score']} is below the 0.8 threshold"
    )


# ── benchmark scenarios ───────────────────────────────────────────────────────

def test_all_benchmarks_pass():
    results = run_benchmarks()
    failed = [r for r in results if not r["passed"]]
    failure_details = "\n".join(
        f"  FAIL: {r['name']}\n    " + "\n    ".join(r["failures"])
        for r in failed
    )
    assert not failed, f"\n{len(failed)} benchmark(s) failed:\n{failure_details}"


def test_benchmark_count_matches_expected():
    from metrics import BENCHMARKS
    results = run_benchmarks()
    assert len(results) == len(BENCHMARKS)
