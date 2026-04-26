"""
PawPal+ Standalone Evaluation Script
=====================================
Run from the project root:
    python eval_script.py

Evaluates the AI planner on all predefined benchmark scenarios and prints
a structured pass/fail report with metric scores.
"""

from metrics import run_benchmarks, BENCHMARKS, evaluate_plan
from agent import build_daily_plan, build_daily_schedule, validate_tasks
from datetime import time


# ── Benchmark evaluation ──────────────────────────────────────────────────────

def run_benchmark_report() -> None:
    print("\n" + "=" * 62)
    print("  PawPal+ AI Planner — Benchmark Evaluation Report")
    print("=" * 62)

    results = run_benchmarks()
    n_pass  = sum(1 for r in results if r["passed"])
    n_total = len(results)

    for r in results:
        badge = "PASS ✓" if r["passed"] else "FAIL ✗"
        print(f"\n  [{badge}]  {r['name']}")
        if r["failures"]:
            for f in r["failures"]:
                print(f"           ✗ {f}")
        else:
            print(f"           Scheduled: {', '.join(r['scheduled_titles']) or '(none)'}")
        m = r["metrics"]
        print(
            f"           Coverage {m['task_coverage']*100:.0f}%  |  "
            f"Efficiency {m['time_efficiency']*100:.0f}%  |  "
            f"Compliance {m['priority_compliance']*100:.0f}%  |  "
            f"Overall {m['overall_score']*100:.0f}%"
        )

    avg_score = sum(r["metrics"]["overall_score"] for r in results) / n_total
    print("\n" + "-" * 62)
    print(f"  TOTAL:  {n_pass}/{n_total} passed  |  Avg overall score: {avg_score*100:.1f}%")
    verdict = "ALL BENCHMARKS PASSED" if n_pass == n_total else f"{n_total - n_pass} BENCHMARK(S) FAILED"
    print(f"  RESULT: {verdict}")
    print("=" * 62 + "\n")


# ── Custom spot-check scenarios ───────────────────────────────────────────────

SPOT_CHECKS = [
    {
        "name": "Fixed task placed at exact time",
        "window": (time(8, 0), time(12, 0)),
        "tasks": [
            {"title": "Give medicine", "duration_minutes": 5, "priority": "high",
             "fixed_start_time": "09:00"},
        ],
        "expect": {"09:00": "Give medicine"},
    },
    {
        "name": "High priority wins over low when window is tight",
        "window": (time(8, 0), time(8, 30)),
        "tasks": [
            {"title": "Walk",  "duration_minutes": 20, "priority": "high"},
            {"title": "Bath",  "duration_minutes": 20, "priority": "low"},
        ],
        "expect_in":  ["Walk"],
        "expect_out": ["Bath"],
    },
    {
        "name": "Morning-preferred task lands before noon",
        "window": (time(8, 0), time(18, 0)),
        "tasks": [
            {"title": "Morning walk", "duration_minutes": 30,
             "priority": "medium", "preferred_time": "morning"},
        ],
        "before_noon": ["Morning walk"],
    },
    {
        "name": "Overlapping fixed tasks — second is rejected",
        "window": (time(8, 0), time(12, 0)),
        "tasks": [
            {"title": "Task A", "duration_minutes": 30, "priority": "high",
             "fixed_start_time": "09:00"},
            {"title": "Task B", "duration_minutes": 20, "priority": "high",
             "fixed_start_time": "09:15"},
        ],
        "expect_in":  ["Task A"],
        "expect_out": ["Task B"],
    },
]


def run_spot_checks() -> None:
    print("=" * 62)
    print("  PawPal+ AI Planner — Spot-Check Scenarios")
    print("=" * 62)

    n_pass, n_total = 0, len(SPOT_CHECKS)

    for sc in SPOT_CHECKS:
        ws, we = sc["window"]
        scheduled, unscheduled = build_daily_schedule(ws, we, sc["tasks"])
        scheduled_titles   = {e["title"] for e in scheduled}
        unscheduled_titles = {t["title"] for t in unscheduled}

        failures = []

        for title in sc.get("expect_in", []):
            if title not in scheduled_titles:
                failures.append(f"'{title}' should be scheduled but wasn't")
        for title in sc.get("expect_out", []):
            if title in scheduled_titles:
                failures.append(f"'{title}' should NOT be scheduled but was")
        for start_fmt, title in sc.get("expect", {}).items():
            match = next((e for e in scheduled if e["title"] == title), None)
            if not match:
                failures.append(f"'{title}' not scheduled at all")
            elif match["start_fmt"] != start_fmt and match["start_fmt"] != _to12(start_fmt):
                failures.append(f"'{title}' placed at {match['start_fmt']}, expected {start_fmt}")
        for title in sc.get("before_noon", []):
            match = next((e for e in scheduled if e["title"] == title), None)
            if not match:
                failures.append(f"'{title}' not scheduled")
            elif match["start_time"].hour >= 12:
                failures.append(f"'{title}' placed at {match['start_fmt']}, should be before noon")

        passed = len(failures) == 0
        if passed:
            n_pass += 1
        badge = "PASS ✓" if passed else "FAIL ✗"
        print(f"\n  [{badge}]  {sc['name']}")
        if failures:
            for f in failures:
                print(f"           ✗ {f}")
        else:
            placed = ", ".join(sorted(scheduled_titles)) or "(none)"
            print(f"           Scheduled: {placed}")

    print("\n" + "-" * 62)
    print(f"  TOTAL: {n_pass}/{n_total} spot-checks passed")
    print("=" * 62 + "\n")


def _to12(s: str) -> str:
    """Convert '09:00' to '9:00 AM' for comparison."""
    from agent import _parse_time_str, _fmt
    try:
        return _fmt(_parse_time_str(s))
    except Exception:
        return s


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    run_benchmark_report()
    run_spot_checks()
