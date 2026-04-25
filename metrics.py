"""
Performance metrics for the PawPal+ AI planner.

Three measurable scores (each 0.0 – 1.0):
  - task_coverage       : fraction of submitted tasks that were scheduled
  - time_efficiency     : fraction of available time actually used
  - priority_compliance : no lower-priority task was scheduled while a
                          higher-priority one was left out

evaluate_plan() combines all three into an overall_score.
run_benchmarks() runs every predefined scenario and returns pass/fail results.
"""

from __future__ import annotations
from typing import Any, Dict, List, Tuple

from agent import build_daily_plan, validate_tasks


# ── helpers ───────────────────────────────────────────────────────────────────

def _pval(task: Dict[str, Any]) -> int:
    return {"high": 3, "medium": 2, "low": 1}.get(
        (task.get("priority") or "low").lower(), 1
    )


# ── individual metrics ────────────────────────────────────────────────────────

def task_coverage(tasks: List[Dict], schedule: List[Dict]) -> float:
    """Fraction of valid tasks that were scheduled (0.0 – 1.0)."""
    valid = validate_tasks(tasks)
    if not valid:
        return 1.0
    return len(schedule) / len(valid)


def time_efficiency(schedule: List[Dict], available_minutes: int) -> float:
    """Fraction of available time used by the schedule (capped at 1.0)."""
    if available_minutes <= 0:
        return 0.0
    used = sum(t["duration_minutes"] for t in schedule)
    return min(used / available_minutes, 1.0)


def priority_compliance(tasks: List[Dict], schedule: List[Dict]) -> float:
    """
    Measures whether the planner respected priority order.

    A violation occurs when a task with higher priority was left unscheduled
    while a task with lower (or equal) priority was included.
    Returns 1.0 when there are no violations.
    """
    scheduled_titles = {t["title"] for t in schedule}
    unscheduled = [t for t in validate_tasks(tasks) if t["title"] not in scheduled_titles]

    if not unscheduled:
        return 1.0

    violations = 0
    comparisons = 0
    for u in unscheduled:
        for s in schedule:
            comparisons += 1
            if _pval(u) > _pval(s):
                violations += 1

    if comparisons == 0:
        return 1.0
    return round(1.0 - violations / comparisons, 4)


# ── combined evaluation ───────────────────────────────────────────────────────

def evaluate_plan(
    tasks: List[Dict],
    schedule: List[Dict],
    available_minutes: int,
) -> Dict[str, float]:
    """
    Return a dict with four scores (all 0.0 – 1.0 / 100 %):
      task_coverage, time_efficiency, priority_compliance, overall_score
    """
    cov = task_coverage(tasks, schedule)
    eff = time_efficiency(schedule, available_minutes)
    comp = priority_compliance(tasks, schedule)
    overall = round((cov + eff + comp) / 3, 4)
    return {
        "task_coverage": round(cov, 4),
        "time_efficiency": round(eff, 4),
        "priority_compliance": round(comp, 4),
        "overall_score": overall,
    }


# ── benchmark scenarios ───────────────────────────────────────────────────────

BENCHMARKS: List[Dict[str, Any]] = [
    {
        "name": "High priority scheduled when time is tight",
        "tasks": [
            {"title": "Give medicine", "duration_minutes": 5,  "priority": "high"},
            {"title": "Playtime",      "duration_minutes": 60, "priority": "low"},
        ],
        "available_minutes": 30,
        "expect_in": ["Give medicine"],
        "expect_out": ["Playtime"],
    },
    {
        "name": "All tasks fit when time is ample",
        "tasks": [
            {"title": "Feed breakfast", "duration_minutes": 10, "priority": "high"},
            {"title": "Morning walk",   "duration_minutes": 30, "priority": "medium"},
            {"title": "Brush fur",      "duration_minutes": 10, "priority": "low"},
        ],
        "available_minutes": 120,
        "expect_in": ["Feed breakfast", "Morning walk", "Brush fur"],
        "expect_out": [],
    },
    {
        "name": "Medium scheduled before low when time is limited",
        "tasks": [
            {"title": "Medium task", "duration_minutes": 20, "priority": "medium"},
            {"title": "Low task",    "duration_minutes": 20, "priority": "low"},
        ],
        "available_minutes": 20,
        "expect_in": ["Medium task"],
        "expect_out": ["Low task"],
    },
    {
        "name": "Invalid tasks (no title / zero duration) are filtered",
        "tasks": [
            {"title": "",      "duration_minutes": 10, "priority": "high"},
            {"title": "Walk",  "duration_minutes": 0,  "priority": "high"},
            {"title": "Feed",  "duration_minutes": 10, "priority": "medium"},
        ],
        "available_minutes": 60,
        "expect_in": ["Feed"],
        "expect_out": [],
    },
    {
        "name": "Preferred-time bonus breaks priority tie correctly",
        "tasks": [
            {"title": "Task A", "duration_minutes": 10, "priority": "medium", "preferred_time": "morning"},
            {"title": "Task B", "duration_minutes": 10, "priority": "medium"},
        ],
        "available_minutes": 10,
        "expect_in": ["Task A"],
        "expect_out": ["Task B"],
    },
    {
        "name": "Empty task list returns empty schedule without error",
        "tasks": [],
        "available_minutes": 60,
        "expect_in": [],
        "expect_out": [],
    },
]


def run_benchmarks() -> List[Dict[str, Any]]:
    """
    Run every benchmark scenario through build_daily_plan.

    Returns a list of result dicts with keys:
      name, passed, scheduled_titles, metrics, failures
    """
    results = []
    for scenario in BENCHMARKS:
        tasks = scenario["tasks"]
        available = scenario["available_minutes"]
        schedule, _ = build_daily_plan(None, None, tasks, available)
        scheduled_titles = {t["title"] for t in schedule}

        failures = []
        for title in scenario["expect_in"]:
            if title not in scheduled_titles:
                failures.append(f"'{title}' should be scheduled but wasn't")
        for title in scenario["expect_out"]:
            if title in scheduled_titles:
                failures.append(f"'{title}' should NOT be scheduled but was")

        metrics = evaluate_plan(tasks, schedule, available) if tasks else {
            "task_coverage": 1.0, "time_efficiency": 1.0,
            "priority_compliance": 1.0, "overall_score": 1.0,
        }

        results.append({
            "name": scenario["name"],
            "passed": len(failures) == 0,
            "scheduled_titles": sorted(scheduled_titles),
            "metrics": metrics,
            "failures": failures,
        })
    return results
