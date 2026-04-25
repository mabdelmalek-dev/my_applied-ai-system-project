from datetime import date, time, datetime, timezone, timedelta
import pytest

from pawpal_system import Owner, Pet, Task
from agent import PawPalAgent


def _owner(tasks_data, avail=None):
    """Build a minimal Owner + single Pet + tasks fixture."""
    owner = Owner(id=1, name="Test Owner")
    owner.set_availability(
        avail or [{"start": time(8, 0), "end": time(18, 0)}]
    )
    pet = Pet(id=1, name="Buddy", species="dog")
    owner.add_pet(pet)
    for i, td in enumerate(tasks_data, start=1):
        t = Task(
            id=i,
            pet_id=pet.id,
            title=td.get("title", f"Task {i}"),
            duration_minutes=td.get("duration_minutes", 10),
            priority=td.get("priority", 2),
            priority_level=td.get("priority_level", "medium"),
            recurrence_rule=td.get("recurrence_rule"),
            active=td.get("active", True),
        )
        pet.add_task(t)
    return owner


# ------------------------------------------------------------------
# Decision coverage
# ------------------------------------------------------------------

def test_decisions_produced_for_every_active_task():
    owner = _owner([
        {"title": "Feed", "duration_minutes": 10, "priority_level": "high"},
        {"title": "Walk", "duration_minutes": 30, "priority_level": "medium"},
    ])
    _, decisions = PawPalAgent(owner).run(date.today())
    assert len(decisions) == 2
    assert {d.task.title for d in decisions} == {"Feed", "Walk"}


def test_inactive_task_excluded_from_decisions():
    owner = _owner([
        {"title": "Active", "duration_minutes": 10, "active": True},
        {"title": "Inactive", "duration_minutes": 10, "active": False},
    ])
    _, decisions = PawPalAgent(owner).run(date.today())
    titles = {d.task.title for d in decisions}
    assert "Inactive" not in titles
    assert "Active" in titles


def test_empty_task_list_returns_empty_schedule():
    owner = Owner(id=1, name="No Tasks")
    pet = Pet(id=1, name="Cat", species="cat")
    owner.add_pet(pet)
    owner.set_availability([{"start": time(8, 0), "end": time(18, 0)}])
    plan, decisions = PawPalAgent(owner).run(date.today())
    assert decisions == []
    assert len(plan.entries) == 0


# ------------------------------------------------------------------
# Priority and scheduling
# ------------------------------------------------------------------

def test_high_priority_task_always_scheduled():
    owner = _owner([
        {"title": "Low task", "duration_minutes": 10, "priority": 1, "priority_level": "low"},
        {"title": "High task", "duration_minutes": 10, "priority": 3, "priority_level": "high"},
    ])
    _, decisions = PawPalAgent(owner).run(date.today())
    scheduled_titles = {d.task.title for d in decisions if d.scheduled}
    assert "High task" in scheduled_titles


def test_task_exceeding_availability_not_scheduled():
    # 60 min available, task needs 120 min
    owner = _owner(
        [{"title": "Too Long", "duration_minutes": 120, "priority_level": "high"}],
        avail=[{"start": time(8, 0), "end": time(9, 0)}],
    )
    _, decisions = PawPalAgent(owner).run(date.today())
    assert len(decisions) == 1
    d = decisions[0]
    assert not d.scheduled
    assert "availability" in d.reason.lower() or "slot" in d.reason.lower()


# ------------------------------------------------------------------
# Explanations
# ------------------------------------------------------------------

def test_scheduled_task_reason_includes_time_range():
    owner = _owner([
        {"title": "Morning Feed", "duration_minutes": 15, "priority_level": "high"},
    ])
    _, decisions = PawPalAgent(owner).run(date.today())
    scheduled = [d for d in decisions if d.scheduled]
    assert len(scheduled) == 1
    assert ":" in scheduled[0].reason  # HH:MM time present


def test_unscheduled_task_reason_is_non_empty():
    owner = _owner(
        [{"title": "Impossible", "duration_minutes": 999, "priority_level": "low"}],
        avail=[{"start": time(8, 0), "end": time(8, 30)}],
    )
    _, decisions = PawPalAgent(owner).run(date.today())
    assert decisions[0].reason.strip() != ""


# ------------------------------------------------------------------
# Summary and trace
# ------------------------------------------------------------------

def test_summary_contains_required_sections():
    owner = _owner([
        {"title": "Short", "duration_minutes": 5, "priority_level": "high"},
        {"title": "Too Long", "duration_minutes": 999, "priority_level": "low"},
    ], avail=[{"start": time(8, 0), "end": time(8, 30)}])
    agent = PawPalAgent(owner)
    agent.run(date.today())
    summary = agent.summary()
    assert "SCHEDULED" in summary
    assert "NOT SCHEDULED" in summary
    assert "REASONING TRACE" in summary


def test_reasoning_trace_populated_with_all_steps():
    owner = _owner([{"title": "Walk", "duration_minutes": 20}])
    agent = PawPalAgent(owner)
    agent.run(date.today())
    full_trace = "\n".join(agent.trace)
    assert "Observe" in full_trace
    assert "Evaluate" in full_trace
    assert "Plan" in full_trace
    assert "Explain" in full_trace


# ------------------------------------------------------------------
# Availability defaults
# ------------------------------------------------------------------

def test_default_availability_set_when_missing():
    owner = Owner(id=1, name="No Avail")
    pet = Pet(id=1, name="Dog", species="dog")
    owner.add_pet(pet)
    pet.add_task(Task(id=1, pet_id=1, title="Feed", duration_minutes=10, priority_level="medium"))
    # no availability set on owner
    agent = PawPalAgent(owner)
    _, decisions = agent.run(date.today())
    assert len(decisions) == 1
    assert owner.availability  # agent filled it in
