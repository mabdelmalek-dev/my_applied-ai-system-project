from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, date, time, timedelta, timezone
from typing import List, Dict, Optional, Any


@dataclass
class Pet:
	id: Optional[int] = None
	name: str = ""
	species: str = ""
	breed: Optional[str] = None
	sex: Optional[str] = None
	age: Optional[int] = None
	photo_url: Optional[str] = None
	notes: List[str] = field(default_factory=list)
	tasks: List["Task"] = field(default_factory=list)
	owner_id: Optional[int] = None
	default_routines: List[Dict[str, Any]] = field(default_factory=list)
	medical_needs: List[Dict[str, Any]] = field(default_factory=list)
	created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
	updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

	def update_profile(self, data: Dict[str, Any]) -> None:
		"""Update pet attributes from a mapping of fields to values."""
		for k, v in data.items():
			if hasattr(self, k):
				setattr(self, k, v)
		self.updated_at = datetime.now(timezone.utc)

	def add_note(self, text: str) -> None:
		"""Append a free-text note to the pet's notes list."""
		self.notes.append(text)
		self.updated_at = datetime.now(timezone.utc)

	def get_routines(self) -> List[Dict[str, Any]]:
		"""Return a copy of the pet's default routines."""
		return list(self.default_routines)

	def age_in_years(self) -> Optional[int]:
		"""Return the pet's age in years (if known)."""
		return self.age

	def add_task(self, task: "Task") -> None:
		"""Attach a Task to this pet."""
		self.tasks.append(task)
		self.updated_at = datetime.now(timezone.utc)

	def remove_task(self, task_id: int) -> None:
		"""Remove a task from the pet by its id."""
		self.tasks = [t for t in self.tasks if t.id != task_id]
		self.updated_at = datetime.now(timezone.utc)

	def get_tasks(self) -> List["Task"]:
		"""Return a shallow copy of tasks assigned to this pet."""
		return list(self.tasks)


@dataclass
class Owner:
	id: Optional[int] = None
	name: str = ""
	email: Optional[str] = None
	phone: Optional[str] = None
	timezone: Optional[str] = None
	availability: List[Dict[str, Any]] = field(default_factory=list)
	preferences: Dict[str, Any] = field(default_factory=dict)
	emergency_contact: Optional[Dict[str, Any]] = None
	notification_settings: Dict[str, Any] = field(default_factory=dict)
	pets: List[Pet] = field(default_factory=list)
	created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
	updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

	def set_availability(self, windows: List[Dict[str, Any]]) -> None:
		"""Set the owner's daily availability windows."""
		self.availability = windows
		self.updated_at = datetime.now(timezone.utc)

	def update_preferences(self, prefs: Dict[str, Any]) -> None:
		"""Update owner preferences with the provided mapping."""
		self.preferences.update(prefs)
		self.updated_at = datetime.now(timezone.utc)

	def notify(self, message: str, channel: Optional[str] = None) -> None:
		"""Send or enqueue a notification for the owner (placeholder)."""
		# placeholder: in real app this would enqueue or send a message
		print(f"Notify {self.name} via {channel or 'default'}: {message}")


	def is_available(self, dt_range: Dict[str, datetime]) -> bool:
		"""Check whether the owner is available for the given datetime range."""
		# basic check against availability windows (expects 'start' and 'end' datetimes)
		start = dt_range.get("start")
		end = dt_range.get("end")
		if not start or not end:
			return False
		for w in self.availability:
			wstart: time = w.get("start")
			wend: time = w.get("end")
			if not wstart or not wend:
				continue
			ws = datetime.combine(start.date(), wstart)
			we = datetime.combine(start.date(), wend)
			if start >= ws and end <= we:
				return True
		return False

	def add_pet(self, pet: Pet) -> None:
		"""Attach a Pet to this owner."""
		self.pets.append(pet)
		self.updated_at = datetime.now(timezone.utc)

	def remove_pet(self, pet_id: int) -> None:
		"""Remove a pet from this owner by id."""
		self.pets = [p for p in self.pets if p.id != pet_id]
		self.updated_at = datetime.now(timezone.utc)

	def get_all_tasks(self) -> List["Task"]:
		"""Return all tasks across all pets owned by this owner."""
		all_tasks: List[Task] = []
		for p in self.pets:
			all_tasks.extend(p.get_tasks())
		return all_tasks

	def get_tasks_filtered(self, pet_id: Optional[int] = None, active: Optional[bool] = None) -> List["Task"]:
		"""Return tasks optionally filtered by pet id and active flag."""
		tasks = self.get_all_tasks()
		if pet_id is not None:
			tasks = [t for t in tasks if t.pet_id == pet_id]
		if active is not None:
			tasks = [t for t in tasks if t.active == active]
		return tasks


@dataclass
class Task:
	id: Optional[int] = None
	pet_id: Optional[int] = None
	title: str = ""
	type: str = ""  # e.g., walk, feed, med
	duration_minutes: int = 0
	priority: int = 0
	recurrence_rule: Optional[str] = None
	earliest_time: Optional[time] = None
	latest_time: Optional[time] = None
	requires_walker: bool = False
	notes: Optional[str] = None
	estimated_effort: Optional[int] = None
	last_performed: Optional[datetime] = None
	active: bool = True
	created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
	updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

	def create_or_update(self, fields: Dict[str, Any]) -> None:
		"""Update task fields from a mapping of field names to values."""
		for k, v in fields.items():
			if hasattr(self, k):
				setattr(self, k, v)
		self.updated_at = datetime.now(timezone.utc)

	def reschedule(self, new_rule: str) -> None:
		"""Set a new recurrence rule for the task."""
		self.recurrence_rule = new_rule
		self.updated_at = datetime.now(timezone.utc)

	def activate(self) -> None:
		"""Mark the task active so it is considered by the scheduler."""
		self.active = True
		self.updated_at = datetime.now(timezone.utc)

	def deactivate(self) -> None:
		"""Disable the task so the scheduler ignores it."""
		self.active = False
		self.updated_at = datetime.now(timezone.utc)

	def mark_done(self, date_or_instance_id: Optional[Any] = None) -> None:
		"""Record that the task was performed now (updates last_performed)."""
		self.last_performed = datetime.now(timezone.utc)
		self.updated_at = datetime.now(timezone.utc)

	def conflicts_with(self, other: "Task") -> bool:
		"""Quick check for conflicts between two tasks (heuristic)."""
		# Simple heuristic: tasks conflict if both require a walker at overlapping allowed windows.
		if not self.requires_walker or not other.requires_walker:
			return False
		if self.earliest_time and self.latest_time and other.earliest_time and other.latest_time:
			start_a = datetime.combine(date.today(), self.earliest_time)
			end_a = datetime.combine(date.today(), self.latest_time)
			start_b = datetime.combine(date.today(), other.earliest_time)
			end_b = datetime.combine(date.today(), other.latest_time)
			return not (end_a <= start_b or end_b <= start_a)
		return False

	def to_instance(self, on_date: date) -> "TaskInstance":
		"""Create a TaskInstance for the provided date using default fields."""
		return TaskInstance(task_id=self.id, date=on_date)

	def is_scheduled_on(self, on_date: date) -> bool:
		"""Simple recurrence rule matcher. Supported rules:
		- None / empty: always True
		- 'daily'
		- 'weekdays' (mon-fri)
		- 'weekends' (sat-sun)
		- comma-separated short day names like 'mon,tue'
		"""
		if not self.recurrence_rule:
			return True
		r = self.recurrence_rule.strip().lower()
		if r == "daily":
			return True
		if r == "weekdays":
			return on_date.weekday() < 5
		if r == "weekends":
			return on_date.weekday() >= 5
		# allow patterns like 'mon,tue'
		short_names = {0: "mon", 1: "tue", 2: "wed", 3: "thu", 4: "fri", 5: "sat", 6: "sun"}
		parts = [p.strip() for p in r.split(",") if p.strip()]
		if parts:
			today = short_names[on_date.weekday()]
			return today in parts
		# unknown rule: default to False to avoid accidental scheduling
		return False


@dataclass
class TaskInstance:
	id: Optional[int] = None
	task_id: Optional[int] = None
	date: Optional[date] = None
	scheduled_start: Optional[datetime] = None
	scheduled_end: Optional[datetime] = None
	status: str = "planned"  # planned/done/cancelled
	assigned_person: Optional[int] = None
	actual_start: Optional[datetime] = None
	actual_end: Optional[datetime] = None
	notes: Optional[str] = None
	reminder_id: Optional[int] = None
	created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
	updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

	def mark_done(self, actual_start: Optional[datetime] = None, actual_end: Optional[datetime] = None) -> None:
		"""Mark this TaskInstance as completed and record actual times."""
		self.status = "done"
		if actual_start:
			self.actual_start = actual_start
		if actual_end:
			self.actual_end = actual_end
		self.updated_at = datetime.now(timezone.utc)

	def postpone(self, new_start: datetime) -> None:
		"""Postpone the scheduled start to a new datetime, keeping duration."""
		# shift scheduled times by keeping duration
		duration = None
		if self.scheduled_start and self.scheduled_end:
			duration = self.scheduled_end - self.scheduled_start
		self.scheduled_start = new_start
		if duration:
			self.scheduled_end = new_start + duration
		self.updated_at = datetime.now(timezone.utc)

	def cancel(self, reason: Optional[str] = None) -> None:
		"""Cancel this TaskInstance and optionally record a reason."""
		self.status = "cancelled"
		if reason:
			self.notes = (self.notes or "") + f"\nCancelled: {reason}"
		self.updated_at = datetime.now(timezone.utc)

	def assign_person(self, person_id: int) -> None:
		"""Assign a person id responsible for executing this TaskInstance."""
		self.assigned_person = person_id
		self.updated_at = datetime.now(timezone.utc)

	def duration_minutes(self) -> Optional[int]:
		"""Return the duration in whole minutes if start/end times are known."""
		if self.scheduled_start and self.scheduled_end:
			return int((self.scheduled_end - self.scheduled_start).total_seconds() // 60)
		if self.actual_start and self.actual_end:
			return int((self.actual_end - self.actual_start).total_seconds() // 60)
		return None

	def explain_reason(self) -> str:
		"""Return a short human-readable explanation for this TaskInstance."""
		return "No explanation provided."


@dataclass
class Constraints:
	id: Optional[int] = None
	owner_id: Optional[int] = None
	max_daily_duration: Optional[int] = None
	preferred_time_windows: List[Dict[str, Any]] = field(default_factory=list)
	blocked_times: List[Dict[str, Any]] = field(default_factory=list)
	priority_weights: Dict[str, float] = field(default_factory=dict)
	pet_specific_rules: Dict[str, Any] = field(default_factory=dict)
	allowed_task_types: List[str] = field(default_factory=list)
	minimum_gap_between_tasks: Optional[int] = None

	def is_allowed(self, task: Task, slot: Dict[str, datetime]) -> bool:
		"""Return whether a task is allowed to be scheduled in the given slot."""
		raise NotImplementedError

	def apply_owner_preferences(self, schedule: "DailySchedule") -> None:
		"""Adjust a schedule in-place according to owner preferences."""
		raise NotImplementedError


class Scheduler:
	"""Planner that generates a DailySchedule from tasks, owner availability, and constraints."""

	def __init__(self,
				 date: Optional[date] = None,
				 owner_id: Optional[int] = None,
				 task_pool: Optional[List[Task]] = None,
				 constraints: Optional[Constraints] = None,
				 scoring_weights: Optional[Dict[str, float]] = None,
				 time_slots: Optional[List[Dict[str, datetime]]] = None) -> None:
		self.date = date
		self.owner_id = owner_id
		self.task_pool: List[Task] = task_pool or []
		self.constraints = constraints
		self.scoring_weights = scoring_weights or {}
		self.time_slots = time_slots or []
		self.generated_schedule_id: Optional[int] = None
		self.run_metadata: Dict[str, Any] = {}

	def generate_plan(self) -> DailySchedule:
		"""Generate a DailySchedule by greedily fitting high-priority tasks into availability."""
		# Basic greedy scheduler that fills owner availability with highest-priority tasks.
		if not self.date:
			on_date = date.today()
		else:
			on_date = self.date
		# owner must be provided via owner_id or by passing owner object in run_metadata
		owner: Optional[Owner] = self.run_metadata.get("owner")
		if owner is None:
			raise ValueError("Owner instance required in Scheduler.run_metadata['owner']")

		schedule = DailySchedule(date=on_date, owner_id=owner.id)
		# gather tasks and respect recurrence rules
		tasks = [t for t in owner.get_all_tasks() if t.active and t.is_scheduled_on(on_date)]
		# dynamic greedy selection using scoring and 1-step lookahead
		# initial sort is not strictly necessary but keeps ordering stable
		tasks.sort(key=lambda x: (-x.priority, x.duration_minutes or 0))

		# iterate availability windows
		for w in owner.availability:
			wstart: time = w.get("start")
			wend: time = w.get("end")
			if not wstart or not wend:
				continue
			current = datetime.combine(on_date, wstart)
			window_end = datetime.combine(on_date, wend)
			while current < window_end and tasks:
				assigned = False
				candidates = []
				for i, task in enumerate(tasks):
					# check fit
					req = timedelta(minutes=task.duration_minutes)
					if current + req <= window_end:
						slot = {"start": current, "end": current + req}
						score = self.score_task_for_slot(task, slot)
						candidates.append((i, task, req, score))
				# if no candidates fit remaining time, break
				if not candidates:
					break
				# 1-step lookahead: for each candidate, simulate picking it then best next candidate in remaining time
				best_choice = None
				best_value = float("-inf")
				alpha = 0.0
				for (i, task, req, score) in candidates:
					# simulate remaining time after placing this task
					next_current = current + req
					remaining_candidates = []
					for j, oth in enumerate(tasks):
						if j == i:
							continue
						req2 = timedelta(minutes=oth.duration_minutes)
						if next_current + req2 <= window_end:
							slot2 = {"start": next_current, "end": next_current + req2}
							score2 = self.score_task_for_slot(oth, slot2)
							remaining_candidates.append(score2)
					# best next score (0 if none)
					best_next = max(remaining_candidates) if remaining_candidates else 0.0
					# combine with weighted lookahead (alpha controls lookahead influence)
					value = score + alpha * best_next
					if value > best_value:
						best_value = value
						best_choice = (i, task, req)

				# commit best choice
				if best_choice:
					i, task, req = best_choice
					ti = TaskInstance(task_id=task.id, date=on_date, scheduled_start=current, scheduled_end=current + req)
					schedule.add_entry(ti)
					# mark task as scheduled once
					tasks.pop(i)
					current = ti.scheduled_end
					assigned = True
				else:
					break

		return schedule

	def detect_conflicts(self, schedule: DailySchedule) -> List[tuple]:
		"""Detect simple conflicts in a schedule.

		Conflicts detected:
		- overlapping TaskInstances
		- overlapping tasks that both require a walker
		Returns list of (TaskInstance, TaskInstance, reason)
		"""
		conflicts = []
		entries = schedule.get_today_tasks()
		for i in range(len(entries)):
			for j in range(i + 1, len(entries)):
				a = entries[i]
				b = entries[j]
				# if either has no times, skip overlap detection
				if not a.scheduled_start or not a.scheduled_end or not b.scheduled_start or not b.scheduled_end:
					continue
				# check overlap
				if not (a.scheduled_end <= b.scheduled_start or b.scheduled_end <= a.scheduled_start):
					# overlapping in time
					reason = "time overlap"
					# check for resource conflict: both require walker
					task_a = next((t for t in self.run_metadata.get("owner").get_all_tasks() if t.id == a.task_id), None)
					task_b = next((t for t in self.run_metadata.get("owner").get_all_tasks() if t.id == b.task_id), None)
					if task_a and task_b and task_a.requires_walker and task_b.requires_walker:
						reason = "walker conflict"
					conflicts.append((a, b, reason))
		return conflicts

	def score_task_for_slot(self, task: Task, slot: Dict[str, datetime]) -> float:
		"""Return a numeric score representing how well a task fits a slot.

		Scoring components (linear combination):
		- priority (higher better)
		- recency penalty (prefer tasks that haven't run recently)
		- duration penalty (prefer shorter tasks slightly)
		- time-window fit bonus (prefer tasks whose earliest/latest match the slot)
		"""
		score = 0.0
		# priority weight (normalized)
		priority_weight = 1.0
		score += priority_weight * float(task.priority or 0)

		# recency: prefer tasks that haven't been performed recently
		if task.last_performed:
			delta_days = (datetime.now(timezone.utc) - task.last_performed).total_seconds() / 86400.0
			recency_score = 1.0 / (1.0 + delta_days)
		else:
			# never performed gets a moderate bonus
			recency_score = 1.0
		score += 2.0 * recency_score

		# duration penalty: prefer shorter tasks (smaller negative contribution)
		if task.duration_minutes:
			score -= 0.01 * float(task.duration_minutes)

		# time-window fit: give bonus if slot lies within earliest/latest
		slot_start = slot.get("start")
		slot_end = slot.get("end")
		if slot_start and slot_end and task.earliest_time and task.latest_time:
			# convert to today's datetimes for comparison
			try:
				es = datetime.combine(slot_start.date(), task.earliest_time)
				le = datetime.combine(slot_start.date(), task.latest_time)
				if slot_start >= es and slot_end <= le:
					score += 1.0
			except Exception:
				pass

		# small penalty for requires_walker (resource constraint) to be resolved elsewhere
		if task.requires_walker:
			score -= 0.5

		return float(score)

	def sort_by_time(self, items: List[Any], time_attr: str = "scheduled_start") -> List[Any]:
		"""Return a new list sorted by a time attribute.

		- `items` may be `Task`, `TaskInstance`, or dict-like objects.
		- `time_attr` is the attribute name to look up on each item (e.g. 'scheduled_start', 'earliest_time', or a string like '08:30').

		Supports values that are `datetime`, `time`, or strings in `HH:MM` format.
		"""

		def to_dt(val):
			if val is None:
				return datetime.min
			if isinstance(val, datetime):
				return val
			if isinstance(val, time):
				return datetime.combine(date.today(), val)
			if isinstance(val, str):
				# try HH:MM or HH:MM:SS
				for fmt in ("%H:%M", "%H:%M:%S"):
					try:
						t = datetime.strptime(val, fmt).time()
						return datetime.combine(date.today(), t)
					except Exception:
						continue
			# fallback
			return datetime.min

		def extract(item):
			# dict-like
			if isinstance(item, dict):
				val = item.get(time_attr)
			else:
				val = getattr(item, time_attr, None)
			return to_dt(val)

		return sorted(list(items), key=extract)

	def fit_tasks_into_availability(self) -> DailySchedule:
		"""Place tasks into available time slots and return a DailySchedule."""
		raise NotImplementedError

	def apply_constraints(self) -> None:
		"""Apply global constraints to the scheduler's internal state."""
		raise NotImplementedError

	def explain_plan(self, schedule: DailySchedule) -> Explanation:
		"""Produce an Explanation object describing why tasks were scheduled."""
		raise NotImplementedError


@dataclass
class DailySchedule:
	id: Optional[int] = None
	date: Optional[date] = None
	owner_id: Optional[int] = None
	entries: List[TaskInstance] = field(default_factory=list)
	total_duration_minutes: int = 0
	summary_text: Optional[str] = None
	explanation_id: Optional[int] = None
	created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
	updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

	def add_entry(self, task_instance: TaskInstance) -> None:
		"""Append a TaskInstance to the schedule and update totals."""
		self.entries.append(task_instance)
		# update total duration if possible
		dur = task_instance.duration_minutes()
		if dur:
			self.total_duration_minutes += dur
		self.updated_at = datetime.now(timezone.utc)

	def remove_entry(self, entry_id: int) -> None:
		"""Remove an entry by id and recompute schedule totals."""
		# remove by id if present, otherwise no-op
		self.entries = [e for e in self.entries if not (e.id == entry_id)]
		# recompute total
		self.total_duration_minutes = sum(filter(None, (e.duration_minutes() for e in self.entries)))
		self.updated_at = datetime.now(timezone.utc)

	def get_today_tasks(self) -> List[TaskInstance]:
		"""Return the list of scheduled TaskInstance objects for the day."""
		# return entries sorted by scheduled_start when possible
		entries = list(self.entries)
		entries.sort(key=lambda e: (e.scheduled_start or datetime.min))
		return entries

	def total_duration(self) -> int:
		"""Return the total scheduled duration in minutes for this schedule."""
		return int(self.total_duration_minutes)

	def export_to_calendar(self, fmt: str = "ics") -> Any:
		"""Export the schedule in a simple format (placeholder)."""
		# simple placeholder: return list of tuples
		return [(e.scheduled_start, e.scheduled_end, e.task_id) for e in self.entries]

	def summarize(self) -> str:
		"""Return a short multi-line summary of the schedule."""
		lines = [f"Date: {self.date}", f"Total duration: {self.total_duration_minutes} minutes", f"Entries: {len(self.entries)}"]
		return "\n".join(lines)


@dataclass
class Notification:
	id: Optional[int] = None
	task_instance_id: Optional[int] = None
	send_time: Optional[datetime] = None
	channel: Optional[str] = None
	message_template: Optional[str] = None
	sent_status: Optional[str] = None
	retry_count: int = 0
	created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
	sent_at: Optional[datetime] = None

	def schedule_send(self) -> None:
		"""Schedule this notification to be sent at `send_time`."""
		raise NotImplementedError

	def send_now(self) -> None:
		"""Send the notification immediately (blocking placeholder)."""
		raise NotImplementedError

	def cancel(self) -> None:
		"""Cancel any scheduled send action for this notification."""
		raise NotImplementedError

	def retry(self) -> None:
		"""Retry sending the notification according to retry policy."""
		raise NotImplementedError

	def mark_sent(self) -> None:
		"""Mark this notification as successfully sent."""
		raise NotImplementedError


@dataclass
class Explanation:
	id: Optional[int] = None
	schedule_id: Optional[int] = None
	entries: Dict[int, List[str]] = field(default_factory=dict)
	summary_text: Optional[str] = None
	generated_by: Optional[str] = None
	created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

	def add_reason(self, task_instance_id: int, reason: str) -> None:
		"""Attach a human-readable reason to a task instance in the explanation."""
		raise NotImplementedError

	def summarize(self) -> str:
		"""Return a human-readable summary of the explanation."""
		raise NotImplementedError

	def to_text(self) -> str:
		"""Render the explanation as plain text."""
		raise NotImplementedError

	def to_json(self) -> Dict[str, Any]:
		"""Serialize the explanation to a JSON-serializable mapping."""
		raise NotImplementedError


class Storage:
	"""Simple repository interface / config holder."""

	def __init__(self, backend_type: str = "json", connection: Optional[str] = None) -> None:
		self.backend_type = backend_type
		self.connection = connection
		self.last_sync: Optional[datetime] = None

	def load_pets(self) -> List[Pet]:
		"""Load and return all pets from the configured backend."""
		raise NotImplementedError

	def save_pet(self, pet: Pet) -> None:
		"""Persist a pet to the configured backend."""
		raise NotImplementedError

	def load_tasks(self) -> List[Task]:
		"""Load and return all tasks from the configured backend."""
		raise NotImplementedError

	def save_task(self, task: Task) -> None:
		"""Persist a task to the configured backend."""
		raise NotImplementedError

	def delete_task(self, task_id: int) -> None:
		"""Delete a task from the configured backend by id."""
		raise NotImplementedError

	def load_schedule(self, on_date: date) -> Optional[DailySchedule]:
		"""Load a saved DailySchedule for a given date, if present."""
		raise NotImplementedError

	def backup(self) -> None:
		"""Perform a backup of the configured backend store."""
		raise NotImplementedError

