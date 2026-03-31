from datetime import datetime, timezone

from pawpal_system import Pet, Task, TaskInstance


def test_taskinstance_mark_done_sets_status():
    ti = TaskInstance(task_id=1)
    assert ti.status == "planned"
    now = datetime.now(timezone.utc)
    ti.mark_done(actual_start=now, actual_end=now)
    assert ti.status == "done"


def test_pet_add_task_increases_count():
    p = Pet(id=1, name="Buddy")
    assert len(p.get_tasks()) == 0
    t = Task(id=1, pet_id=p.id, title="Feed", duration_minutes=10)
    p.add_task(t)
    assert len(p.get_tasks()) == 1
    assert p.get_tasks()[0].title == "Feed"
