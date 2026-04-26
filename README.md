# PawPal+ (Module 2 Project)

You are building **PawPal+**, a Streamlit app that helps a pet owner plan care tasks for their pet.

## Scenario

A busy pet owner needs help staying consistent with pet care. They want an assistant that can:

- Track pet care tasks (walks, feeding, meds, enrichment, grooming, etc.)
- Consider constraints (time available, priority, owner preferences)
- Produce a daily plan and explain why it chose that plan

Your job is to design the system first (UML), then implement the logic in Python, then connect it to the Streamlit UI.

## What you will build

Your final app should:

- Let a user enter basic owner + pet info
- Let a user add/edit tasks (duration + priority at minimum)
- Generate a daily schedule/plan based on constraints and priorities
- Display the plan clearly (and ideally explain the reasoning)
- Include tests for the most important scheduling behaviors

## Getting started

### Setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Suggested workflow

1. Read the scenario carefully and identify requirements and edge cases.
2. Draft a UML diagram (classes, attributes, methods, relationships).
3. Convert UML into Python class stubs (no logic yet).
4. Implement scheduling logic in small increments.
5. Add tests to verify key behaviors.
6. Connect your logic to the Streamlit UI in `app.py`.
7. Refine UML so it matches what you actually built.

## Smarter Scheduling

This project includes a lightweight scheduling engine with a few practical
features to make daily planning useful and explainable:

	combines priority, recency (how recently a task was performed), duration,
	and whether a candidate time fits the task's earliest/latest constraints.
	scheduler briefly considers the best immediate follow-up to avoid locally
	poor choices.
	time and to filter tasks by pet name and completion state.
	and reports warnings (same-pet overlap, walker conflicts, or generic time
	overlaps) instead of raising exceptions so the UI can surface warnings to
	the user and allow manual resolution.

These choices favor clarity, speed, and explainability over perfect
optimality. The code is structured so the heuristic can be replaced with a
solver-backed approach for larger or more constrained cases.

## Features

- Sorting by time: `Scheduler.sort_by_time()` and `DailySchedule.get_today_tasks()` ensure schedule entries are presented in chronological order and handle mixed `datetime`, `time`, and `HH:MM` string formats.
- Conflict warnings: `Scheduler.detect_conflicts()` finds overlapping TaskInstances and reports lightweight warnings (`same-pet overlap`, `walker conflict`, `time overlap`) so the UI can surface actionable messages instead of crashing.
- Daily recurrence: `Task.next_occurrence()` and `Task.mark_done()` automatically compute and (optionally) create the next `TaskInstance` for recurring tasks like `daily`, `weekly`, `weekdays`, and custom day lists.
- Scoring-based greedy planner: `Scheduler.score_task_for_slot()` assigns a heuristic score combining priority, recency, duration penalty, and time-window fit; `Scheduler.generate_plan()` uses a greedy selection with a one-step lookahead.
- Sorting & filtering helpers: Owner and scheduler utilities to filter tasks by pet name or completion and to present sorted schedules in the UI.
- TaskInstance lifecycle helpers:`TaskInstance.postpone()`, `cancel()`, `mark_done()` and `complete(owner)` help manage scheduled instances and trigger recurrence when appropriate.
- Robust datetime handling: The scheduler normalizes naive and timezone-aware datetimes to avoid comparison errors and correctly handle scheduling logic.
- Automated tests: Pytest suite covers sorting, recurrence, and conflict detection (see `tests/test_scheduler.py`).

## 📸 Demo

To embed a screenshot of the final Streamlit app, add the image to your course images folder and use the following Markdown snippet in this README (replace `your_screenshot_name.png`):

<a href="/course_images/ScreenShot.png" target="_blank"><img src='/course_images/ScreenShot.png' title='PawPal App' width='' alt='PawPal App' class='center-block' /></a>

Note: add your actual Streamlit screenshot to `course_images/ai110/ScreenShot.png` (or update the paths above to match your filename). If you'd like, upload the image here and I can add it to the repository for you.

## Agent Mode Challeng 1

Agent Mode was used throughout development to accelerate scaffolding, tests, and iterative implementation. In practice Agent Mode helped with:

- Drafting dataclass scaffolds and method stubs for the domain model.
- Generating unit-test templates for recurrence, sorting, and conflict detection.
- Suggesting small helpers and refactors (datetime normalizers, sort helpers).

All AI-generated suggestions were reviewed, adjusted for clarity, and validated with unit tests and the running Streamlit UI before committing.


## Testing PawPal+

Run the full automated test suite with:

```bash
python -m pytest
```

What the tests cover:

- Sorting correctness: verifies schedule entries are returned in chronological order and handles mixed `datetime`, `time`, and `HH:MM` string representations.
- Recurrence logic: verifies that marking a `daily` task done produces the next `TaskInstance` for the following day.
- Conflict detection: ensures overlapping task instances are detected and reported as warnings (same-pet overlaps, walker/resource conflicts, generic time overlaps).
- Integration scenarios: basic end-to-end checks for scheduling, filtering, and ordering behavior.

Confidence Level: ★★★★☆ (4/5)

Reason: the test suite covers the most common scheduling behaviors and edge cases relevant to the module (sorting, daily recurrence, and simple conflict detection). Further tests for DST transitions, complex recurrence patterns, and larger-scale performance would increase confidence to 5/5.

## System Diagram

The diagram below shows how data flows through PawPal+ from user input to a verified, explained schedule.

```mermaid
flowchart TD
    A([👤 Owner Input\nname · pets · tasks · time window]) --> B

    subgraph UI ["🖥️ Streamlit UI  (app.py)"]
        B[Owner & Pets Tab\nprofile · window · pets]
        C[Tasks Tab\nadd · edit · assign to pet]
        D[Generate Schedule Tab]
        E[AI Reliability Tab]
    end

    B --> C --> D

    subgraph AGENT ["🤖 AI Agent  (agent.py)"]
        F[1 · Validator\nvalidate_tasks\ndrop empty / zero-duration]
        G[2 · Ranker\nrank_tasks\nscore = priority + preferred-time bonus]
        H[3 · Scheduler\nbuild_daily_schedule\nplace fixed slots → then flexible]
        I[4 · Explainer\nexplain_plan\nnatural-language reason per task]
        J[5 · Confidence Scorer\n0–100% per decision\npriority × preferred-time zone]
        F --> G --> H --> I --> J
    end

    D --> F
    J --> K

    subgraph OUTPUT ["📅 Schedule Output"]
        K[Time-slotted schedule table\nwith confidence bars]
        L[Decision Log\nevery accept / reject + reason]
        M[AI Performance Metrics\ncoverage · efficiency · compliance · avg confidence]
    end

    K --> L --> M

    subgraph EVAL ["📊 Evaluator  (metrics.py)"]
        N[evaluate_plan\ntask_coverage · time_efficiency\npriority_compliance · overall_score]
    end

    M --> N

    subgraph TEST ["🧪 Testing Layer"]
        O[Unit Tests · pytest\n55 tests across 5 files\nvalidation · ranking · scheduling · metrics]
        P[Benchmark Scenarios\n6 predefined edge cases\nrun_benchmarks]
        Q[Live Test Runner\nin AI Reliability Tab\npass · fail · full output]
    end

    E --> Q --> O
    E --> P
    N --> P

    subgraph HUMAN ["👁️ Human Evaluation"]
        R[Owner reviews schedule\nin the UI]
        S[Developer reviews\nbenchmark failures]
    end

    K --> R
    P --> S
```

### Component summary

| Component | File | Role |
|---|---|---|
| Streamlit UI | `app.py` | Input collection, schedule display, test runner |
| Validator | `agent.py` | Drops tasks with no title or zero duration |
| Ranker | `agent.py` | Scores tasks by priority + preferred-time bonus |
| Scheduler | `agent.py` | Places fixed tasks first, then flexible by score |
| Explainer | `agent.py` | Generates a plain-English reason for each decision |
| Confidence Scorer | `app.py` | Rates AI certainty per decision (0–100%) |
| Evaluator | `metrics.py` | Measures coverage, efficiency, and compliance |
| Benchmarks | `metrics.py` | 6 predefined scenarios that must always pass |
| Unit Tests | `tests/` | 55 pytest tests covering all core functions |
