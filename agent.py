from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta, timezone
from typing import List, Optional, Tuple

from pawpal_system import Owner, Pet, Task, TaskInstance, Scheduler, DailySchedule


@dataclass
class TaskDecision:
    task: Task
    scheduled: bool
    reason: str
    score: float = 0.0
    slot_start: Optional[datetime] = None
    slot_end: Optional[datetime] = None


class PawPalAgent:
    """
    AI-style agentic workflow for pet care scheduling.

    Loop:
      1. Observe  — collect tasks, availability, and owner preferences
      2. Evaluate — score every active task against all constraints
      3. Plan     — run the greedy scheduler with 1-step lookahead
      4. Explain  — produce a per-task decision and a full reasoning trace
    """

    def __init__(self, owner: Owner) -> None:
        self.owner = owner
        self.trace: List[str] = []
        self.decisions: List[TaskDecision] = []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(self, target_date: Optional[date] = None) -> Tuple[DailySchedule, List[TaskDecision]]:
        """Execute the full agentic loop. Returns (schedule, decisions)."""
        on_date = target_date or date.today()
        self.trace.clear()
        self.decisions.clear()

        # Step 1 — Observe
        self._log(f"[Observe] Date: {on_date}. Owner: {self.owner.name}.")
        all_tasks = self.owner.get_all_tasks()
        active_tasks = [t for t in all_tasks if t.active]
        self._log(
            f"[Observe] {len(active_tasks)} active task(s) across "
            f"{len(self.owner.pets)} pet(s)."
        )
        if not self.owner.availability:
            self.owner.set_availability([{"start": time(8, 0), "end": time(20, 0)}])
            self._log("[Observe] No availability set — defaulting to 08:00–20:00.")
        total_avail = self._total_availability_minutes()
        self._log(f"[Observe] Total available time today: {total_avail} min.")

        if not active_tasks:
            self._log("[Observe] No active tasks — nothing to schedule.")
            empty = DailySchedule(date=on_date, owner_id=self.owner.id)
            return empty, []

        # Step 2 — Evaluate
        self._log("[Evaluate] Scoring tasks against constraints …")
        scored = self._evaluate(active_tasks, on_date)
        for task, score, reason in scored:
            self._log(f"  → '{task.title}'  score={score:.2f}  ({reason})")

        # Step 3 — Plan
        self._log("[Plan] Running scheduler …")
        sched = Scheduler(date=on_date)
        sched.run_metadata["owner"] = self.owner
        schedule = sched.generate_plan()
        self._log(
            f"[Plan] {len(schedule.entries)} task(s) scheduled, "
            f"{schedule.total_duration_minutes} min total."
        )

        # Step 4 — Explain
        self._log("[Explain] Generating per-task decisions …")
        scheduled_ids = {e.task_id for e in schedule.entries}
        id_to_entry = {e.task_id: e for e in schedule.entries}

        for task, score, eval_reason in scored:
            if task.id in scheduled_ids:
                entry = id_to_entry[task.id]
                start = entry.scheduled_start.strftime("%H:%M") if entry.scheduled_start else "?"
                end = entry.scheduled_end.strftime("%H:%M") if entry.scheduled_end else "?"
                reason = (
                    f"Scheduled {start}–{end}. "
                    f"Priority={task.priority_level or task.priority}, "
                    f"duration={task.duration_minutes} min. {eval_reason}."
                )
                self.decisions.append(TaskDecision(
                    task=task, scheduled=True, reason=reason, score=score,
                    slot_start=entry.scheduled_start, slot_end=entry.scheduled_end,
                ))
            else:
                reason = self._rejection_reason(task, on_date, total_avail, eval_reason)
                self.decisions.append(TaskDecision(
                    task=task, scheduled=False, reason=reason, score=score,
                ))

        return schedule, self.decisions

    def summary(self) -> str:
        """Return a plain-text summary of the agent's reasoning and decisions."""
        scheduled = [d for d in self.decisions if d.scheduled]
        skipped = [d for d in self.decisions if not d.scheduled]
        lines = [
            f"PawPal Agent — {len(scheduled)} scheduled, {len(skipped)} not scheduled\n"
        ]
        if scheduled:
            lines.append("SCHEDULED:")
            for d in scheduled:
                lines.append(f"  ✓ {d.task.title}: {d.reason}")
        if skipped:
            lines.append("\nNOT SCHEDULED:")
            for d in skipped:
                lines.append(f"  ✗ {d.task.title}: {d.reason}")
        lines.append("\nREASONING TRACE:")
        lines.extend(f"  {line}" for line in self.trace)
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _evaluate(
        self, tasks: List[Task], on_date: date
    ) -> List[Tuple[Task, float, str]]:
        """Score each task and return [(task, score, short_reason)] sorted high→low."""
        sched = Scheduler()
        results = []
        for task in tasks:
            dummy_start = datetime.combine(on_date, time(8, 0))
            dummy_end = dummy_start + timedelta(minutes=max(task.duration_minutes or 1, 1))
            score = sched.score_task_for_slot(task, {"start": dummy_start, "end": dummy_end})

            parts = []
            prio_map = {"high": 3, "medium": 2, "low": 1}
            pval = prio_map.get((task.priority_level or "").lower(), task.priority or 0)
            parts.append(f"priority={'high' if pval >= 3 else 'medium' if pval == 2 else 'low'}")
            if task.last_performed:
                days_ago = (datetime.now(timezone.utc) - task.last_performed).days
                parts.append(f"last done {days_ago}d ago")
            else:
                parts.append("never performed")
            if task.recurrence_rule:
                parts.append(f"recurrence={task.recurrence_rule}")
            if task.duration_minutes:
                parts.append(f"duration={task.duration_minutes} min")

            results.append((task, score, ", ".join(parts)))

        results.sort(key=lambda x: -x[1])
        return results

    def _rejection_reason(
        self, task: Task, on_date: date, total_avail: int, eval_reason: str
    ) -> str:
        if task.duration_minutes and task.duration_minutes > total_avail:
            return (
                f"Duration ({task.duration_minutes} min) exceeds total "
                f"availability ({total_avail} min). {eval_reason}."
            )
        if not task.is_scheduled_on(on_date):
            return (
                f"Recurrence rule '{task.recurrence_rule}' excludes "
                f"{on_date.strftime('%A')}. {eval_reason}."
            )
        return (
            f"No available slot found — likely displaced by higher-priority tasks. "
            f"{eval_reason}."
        )

    def _total_availability_minutes(self) -> int:
        total = 0
        for w in self.owner.availability:
            s: time = w.get("start")
            e: time = w.get("end")
            if s and e:
                total += int(
                    (
                        datetime.combine(date.today(), e)
                        - datetime.combine(date.today(), s)
                    ).total_seconds()
                    // 60
                )
        return total

    def _log(self, msg: str) -> None:
        self.trace.append(msg)
