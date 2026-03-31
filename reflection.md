# PawPal+ Project Reflection

## 1. System Design

Three core user actions in PawPal+ are:

-Add and manage pet care tasks with duration and priority.

-Generate a daily schedule based on available time and task importance.

-View today's planned tasks with explanations for scheduling decisions.

a. Initial design

- Briefly describe your initial UML design.
I started with a simple design based on the owner, the pet, and the tasks that need to be done each day.

The Owner stores basic information like contact details, available time, and preferences, because these affect scheduling.

The Pet keeps simple pet information such as name, routines, and medical notes that may affect care needs.

A Task represents a care activity like feeding, walking, or medication, with details such as duration and priority.

A TaskInstance is one scheduled version of a task for a specific day and tracks whether it was completed.

Constraints are used to apply rules like available time or preferred task times.

The Scheduler / Planner is the main part that decides which tasks fit into the day and creates a DailySchedule, which is the final ordered list of tasks.

Notification and Explanation support the system by sending reminders and showing why certain tasks were chosen or skipped.

Finally, Storage is used to save tasks and schedules so the information can be reused later.
- What classes did you include, and what responsibilities did you assign to each?

Owner: Keeps basic information about the pet owner, like name, daily free time, and preferences. This helps decide when tasks can be scheduled.

Pet: Stores simple pet details such as name, type of animal, age, and any special care notes.

Task: Describes a care activity like feeding, walking, or giving medicine, including how long it takes and how important it is.

TaskInstance: Represents one specific time a task is planned for a day and whether it is completed or not.

Constraints / Preferences: Holds rules such as available time, preferred hours, or limits on how many tasks fit in one day.

Scheduler / Planner: Chooses which tasks should go into the daily plan based on priority and available time.

DailySchedule: Stores the final list of tasks for the day in order.

Notification / Reminder: Used for reminders so the owner knows when a task should happen.

Explanation: Gives a short reason for why a task was selected or skipped.

Storage / Repository: Saves tasks and schedules so the data can be used later.

b. Design changes

- Did your design change during implementation?
- If yes, describe at least one change and why you made it.

Yes. While moving from the initial UML to code I made a focused change to keep responsibilities clear:

- Added a `Scheduler` class to `pawpal_system.py`. Originally the plan described a scheduler conceptually, but I hadn't created a concrete class for it in the codebase. I added a `Scheduler` skeleton that will own the plan-generation flow (task scoring, fitting tasks into owner availability, applying `Constraints`, and producing a `DailySchedule`).

Why: without a dedicated `Scheduler` the planning logic tends to drift into UI code, task objects, or storage code which makes the algorithm hard to test and evolve. Centralizing planning in `Scheduler` keeps the system modular, makes it easier to unit-test scheduling decisions, and reduces coupling between persistence/UI and the core algorithm.

(If I make further refactors — for example moving `Notification` scheduling to a small `Notifier` service or adding an ID/locking helper for concurrent updates — I'll document them here.)

---

## 2. Scheduling Logic and Tradeoffs

a. Constraints and priorities

- What constraints does your scheduler consider (for example: time, priority, preferences)?
- How did you decide which constraints mattered most?

a. Constraints and priorities

- Constraints the scheduler considers:
	- Owner availability window: the owner's free time each day (earliest/latest times) — tasks must fit inside this window.
	- Task priority: an explicit importance level (high/medium/low) used to prefer certain tasks when time is limited.
	- Duration: how long a task takes; shorter tasks fit more flexibly and long tasks block more of the day.
	- Earliest/latest time windows per task: some tasks are only appropriate at certain hours (e.g., morning meds, evening walk).
	- Recency (how recently a task was done): prefer tasks that haven't been done recently to keep routines balanced.
	- Pet/resource constraints: avoid scheduling overlapping tasks for the same pet or the same resource/person (walker) at the same time.
	- Recurrence rules: respect daily/weekly recurrence patterns so repeating tasks reappear automatically.
	- Owner preferences: soft preferences like preferred time-of-day or breaking up long sessions; treated as scoring nudges rather than hard rules.

- Why these mattered most and how I prioritized them:
	- Primary (hard) constraints: owner availability and task duration are highest priority because a plan that doesn't fit the owner's day is useless. Time-window constraints per task are also treated as near-hard constraints (e.g., medication times).
	- Secondary (scoring) constraints: priority, recency, and owner preferences are used as scoring signals to choose between feasible tasks. They steer the planner toward better choices without making the solver brittle.
	- Safety/resource constraints: same-pet overlaps and resource conflicts are flagged as warnings and avoided where possible — these protect real-world correctness but are surfaced to the user when manual resolution is helpful.

This ordering keeps the scheduler simple and explainable: first ensure feasibility (fits in time and obeys required windows), then use human-readable scores (priority, recency, preferences) to pick among feasible tasks. The approach favors predictable behavior and easy manual tuning over opaque global optimization.

b. Tradeoffs

- Describe one tradeoff your scheduler makes.
- Why is that tradeoff reasonable for this scenario?

One tradeoff the current scheduler makes is using a fast greedy selection with a tiny (one-step) lookahead instead of solving a global optimization (for example, an integer linear program) that would guarantee an optimal ordering.

 - Tradeoff: Greedy + 1-step lookahead vs. global optimal planning.

 - Implication: The greedy approach is much faster and easier to reason about and test, and it keeps the code simple and interactive for a UI-driven workflow. However, it can miss globally optimal schedules — particularly in edge cases where a lower-priority short task should be deferred to make room for a later high-value task whose placement depends on the first decision.

 - Why this is reasonable: For a consumer-facing pet-care helper the task set per day is typically small (a handful of tasks), and responsiveness and explainability matter: owners expect quick results and clear reasoning. The greedy heuristic produces useful schedules quickly and lets us expose simple, human-understandable scoring rules (priority, recency, duration, time-window fit). When stronger guarantees are required, the codebase is structured so a future ILP/CP solver can be added as an optional backend for harder cases.

Decision about a code simplification suggestion:

I reviewed a possible simplification of `score_task_for_slot()` that an AI suggested: condensing the scoring logic into shorter, more "Pythonic" expressions (e.g., single-line computations, more compact recency math, and chained ternaries). While those changes would reduce LOC, they would also make the scoring function harder for future readers (students and maintainers) to inspect and tune. Because the scoring weights are intentionally simple and expected to be tuned by hand, I decided to keep the more explicit, step-by-step implementation — it trades a bit of conciseness for clarity and easier manual tuning.

---

## 3. AI Collaboration

a. How you used AI

- How did you use AI tools during this project (for example: design brainstorming, debugging, refactoring)?
- What kinds of prompts or questions were most helpful?

b. Judgment and verification

- Describe one moment where you did not accept an AI suggestion as-is.
- How did you evaluate or verify what the AI suggested?

---

a. How you used AI

- I used AI in several distinct ways:
	- Design brainstorming and UML drafting (quickly iterating on class responsibilities and relationships).
	- Generating initial code scaffolding (dataclasses, method stubs) so I could focus on algorithmic logic.
	- Producing unit-test templates and example test cases to validate recurrence and conflict detection.
	- Suggesting small refactors and convenience helpers (sort keys, datetime normalizers) that sped up development.

- The most useful prompts were concrete, example-driven requests such as:
	- "Create a dataclass for Task with fields X, Y, Z and a method next_occurrence()."
	- "Write a pytest that checks marking a daily task creates the next day's TaskInstance."
	- "Give a short greedy scoring function combining priority, recency, and duration penalty." 

These focused prompts produced targeted code I could adapt quickly.

b. Judgment and verification

- I did not accept every AI suggestion verbatim. One concrete example: the AI (and Copilot-style completions) sometimes proposed very compact, single-line scoring expressions for `score_task_for_slot()` that used nested ternaries and dense math. I rejected that form in favor of a clearer multi-step implementation.

- How I verified suggestions:
	- I wrote small unit tests immediately around behavior the AI changed (recurrence, sorting, conflict detection).
	- I ran static checks and quick local runs (the Streamlit UI and the demo CLI) to validate runtime behavior.
	- If a suggested change looked risky or hard to read, I refactored it into small, well-named steps so intent stayed clear.

---



## 3. AI Strategy — VS Code Copilot Experience

- Which Copilot features were most effective for building the scheduler?
	- nline completions: saved time when writing repetitive boilerplate like dataclasses, helpers, and simple getters.
	- Whole-line and block suggestions: good for producing method bodies quickly that I then verified and refined.
	- Copilot often suggested pytest-style assertions and fixtures that jump-started the test-first validation loop.

- One AI suggestion I rejected or modified to keep the design clean:
	- Copilot suggested compressing the scoring logic into a single expression that mixed priority weights, recency decay, and time-window penalties. I modified this to an explicit multi-step scoring function with named intermediate values (`priority_score`, `recency_score`, `duration_penalty`) so future readers (and graders) can tweak weights and reason about results.

- How separate chat sessions (or focused prompts) helped:
	- I kept design discussion, implementation, and testing prompts separate. That made the context for each task small and focused so the AI's suggestions were targeted and less likely to mix concerns.
	- Separate sessions made it easier to revert or re-run a line of thought: when a suggested refactor started to drift, I opened a new focused session to explore alternatives without polluting the implementation chat history.

- Summary: lessons as the "lead architect" working with AI tools
	- Treat AI like a senior helper that accelerates boilerplate and offers suggestions — not an autopilot. Keep the high-level architecture and invariants under human control.
	- Use AI to produce many small iterations quickly, but rely on tests and short local runs to validate correctness before committing.
	- Prefer readability and explicitness for core decision logic (scoring, recurrence) — AI can help draft alternatives, but the architect should choose the clearest path.
	- Keep prompts precise and scoped. The clearer the prompt, the more immediately useful the suggestion.

In short: AI multiply productivity, but design responsibility tradeoffs, clarity, and overall architecture stays with the human lead.

---

---

## 4. Testing and Verification

a. What you tested

- Unit tests: I wrote pytest cases that exercise the core scheduler behaviors:
	- Recurrence: `test_next_occurrence_daily` and `test_mark_done_creates_next_instance` verify that marking a `daily` task done produces the next day's `TaskInstance`.
	- Sorting: `test_sort_by_time_mixed_types` and `test_get_today_tasks_ordering` check that schedule entries sort correctly when times are given as datetimes, time objects, or `HH:MM` strings.
	- Conflict detection: `test_detect_conflicts_same_pet` and `test_detect_conflicts_duplicate_times` ensure overlapping `TaskInstance`s produce the expected lightweight warnings.

- Integration / manual checks: I ran the Streamlit UI and the `main.py` demo to verify the scheduling button triggers the planner, the UI displays a chronological plan, and conflict warnings surface in the interface.

- Why these tests matter:
	- These behaviors are the scheduler's core guarantees: correct recurrence, predictable ordering, and safe handling of overlaps. They are easy to break with small refactors, so tests catch regressions early.

b. Confidence

- Current confidence: I feel about 4/5 that the scheduler handles the common, everyday scenarios covered by the tests. The unit tests pass and the demo/Streamlit runs confirm end-to-end behavior for simple examples.

- What I'd test next with more time:
	- Timezone and DST transitions (ensure recurrence and sorting are correct across DST boundaries).
	- More complex recurrence rules (multi-week patterns, exceptions/holidays, and custom day lists).
	- Larger-scale scheduling with many tasks and constrained windows to check performance and greedy heuristics' practical limits.
	- Interaction tests for the Streamlit UI (button actions, session state persistence, and conflict-resolution flows).

---

## 5. Reflection

a. What went well

- What part of this project are you most satisfied with?

b. What you would improve

- If you had another iteration, what would you improve or redesign?

c. Key takeaway

- What is one important thing you learned about designing systems or working with AI on this project?
