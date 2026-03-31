from dataclasses import dataclass, field
from datetime import datetime, date, time
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
	owner_id: Optional[int] = None
	default_routines: List[Dict[str, Any]] = field(default_factory=list)
	medical_needs: List[Dict[str, Any]] = field(default_factory=list)
	created_at: datetime = field(default_factory=datetime.utcnow)
	updated_at: datetime = field(default_factory=datetime.utcnow)

	def update_profile(self, data: Dict[str, Any]) -> None:
		raise NotImplementedError

	def add_note(self, text: str) -> None:
		raise NotImplementedError

	def get_routines(self) -> List[Dict[str, Any]]:
		raise NotImplementedError

	def age_in_years(self) -> Optional[int]:
		raise NotImplementedError


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
	created_at: datetime = field(default_factory=datetime.utcnow)
	updated_at: datetime = field(default_factory=datetime.utcnow)

	def set_availability(self, windows: List[Dict[str, Any]]) -> None:
		raise NotImplementedError

	def update_preferences(self, prefs: Dict[str, Any]) -> None:
		raise NotImplementedError

	def notify(self, message: str, channel: Optional[str] = None) -> None:
		raise NotImplementedError

	def is_available(self, dt_range: Dict[str, datetime]) -> bool:
		raise NotImplementedError


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
	created_at: datetime = field(default_factory=datetime.utcnow)
	updated_at: datetime = field(default_factory=datetime.utcnow)

	def create_or_update(self, fields: Dict[str, Any]) -> None:
		raise NotImplementedError

	def reschedule(self, new_rule: str) -> None:
		raise NotImplementedError

	def activate(self) -> None:
		raise NotImplementedError

	def deactivate(self) -> None:
		raise NotImplementedError

	def mark_done(self, date_or_instance_id: Optional[Any] = None) -> None:
		raise NotImplementedError

	def conflicts_with(self, other: "Task") -> bool:
		raise NotImplementedError

	def to_instance(self, on_date: date) -> "TaskInstance":
		raise NotImplementedError


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
	created_at: datetime = field(default_factory=datetime.utcnow)
	updated_at: datetime = field(default_factory=datetime.utcnow)

	def mark_done(self, actual_start: Optional[datetime] = None, actual_end: Optional[datetime] = None) -> None:
		raise NotImplementedError

	def postpone(self, new_start: datetime) -> None:
		raise NotImplementedError

	def cancel(self, reason: Optional[str] = None) -> None:
		raise NotImplementedError

	def assign_person(self, person_id: int) -> None:
		raise NotImplementedError

	def duration_minutes(self) -> Optional[int]:
		raise NotImplementedError

	def explain_reason(self) -> str:
		raise NotImplementedError


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
		raise NotImplementedError

	def apply_owner_preferences(self, schedule: "DailySchedule") -> None:
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
	created_at: datetime = field(default_factory=datetime.utcnow)
	updated_at: datetime = field(default_factory=datetime.utcnow)

	def add_entry(self, task_instance: TaskInstance) -> None:
		raise NotImplementedError

	def remove_entry(self, entry_id: int) -> None:
		raise NotImplementedError

	def get_today_tasks(self) -> List[TaskInstance]:
		raise NotImplementedError

	def total_duration(self) -> int:
		raise NotImplementedError

	def export_to_calendar(self, fmt: str = "ics") -> Any:
		raise NotImplementedError

	def summarize(self) -> str:
		raise NotImplementedError


@dataclass
class Notification:
	id: Optional[int] = None
	task_instance_id: Optional[int] = None
	send_time: Optional[datetime] = None
	channel: Optional[str] = None
	message_template: Optional[str] = None
	sent_status: Optional[str] = None
	retry_count: int = 0
	created_at: datetime = field(default_factory=datetime.utcnow)
	sent_at: Optional[datetime] = None

	def schedule_send(self) -> None:
		raise NotImplementedError

	def send_now(self) -> None:
		raise NotImplementedError

	def cancel(self) -> None:
		raise NotImplementedError

	def retry(self) -> None:
		raise NotImplementedError

	def mark_sent(self) -> None:
		raise NotImplementedError


@dataclass
class Explanation:
	id: Optional[int] = None
	schedule_id: Optional[int] = None
	entries: Dict[int, List[str]] = field(default_factory=dict)
	summary_text: Optional[str] = None
	generated_by: Optional[str] = None
	created_at: datetime = field(default_factory=datetime.utcnow)

	def add_reason(self, task_instance_id: int, reason: str) -> None:
		raise NotImplementedError

	def summarize(self) -> str:
		raise NotImplementedError

	def to_text(self) -> str:
		raise NotImplementedError

	def to_json(self) -> Dict[str, Any]:
		raise NotImplementedError


class Storage:
	"""Simple repository interface / config holder."""

	def __init__(self, backend_type: str = "json", connection: Optional[str] = None) -> None:
		self.backend_type = backend_type
		self.connection = connection
		self.last_sync: Optional[datetime] = None

	def load_pets(self) -> List[Pet]:
		raise NotImplementedError

	def save_pet(self, pet: Pet) -> None:
		raise NotImplementedError

	def load_tasks(self) -> List[Task]:
		raise NotImplementedError

	def save_task(self, task: Task) -> None:
		raise NotImplementedError

	def delete_task(self, task_id: int) -> None:
		raise NotImplementedError

	def load_schedule(self, on_date: date) -> Optional[DailySchedule]:
		raise NotImplementedError

	def backup(self) -> None:
		raise NotImplementedError

