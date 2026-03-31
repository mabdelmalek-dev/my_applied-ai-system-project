from datetime import date, time
from typing import Optional
import json
import os

from pawpal_system import Owner, Pet, Task, Scheduler


def build_demo_owner_from_dict(data: dict) -> Owner:
    owner = Owner(id=data.get("id", 1), name=data.get("name", "Demo Owner"), email=data.get("email"))
    owner.set_availability(data.get("availability", [{"start": time(8, 0), "end": time(18, 0)}]))

    pets = {}
    for p in data.get("pets", []):
        pet = Pet(id=p.get("id"), name=p.get("name"), species=p.get("species"), age=p.get("age"))
        owner.add_pet(pet)
        pets[pet.id] = pet

    # create tasks and attach to pets
    for t in data.get("tasks", []):
        pet_id = t.get("pet_id")
        task = Task(id=t.get("id"), pet_id=pet_id, title=t.get("title"), type=t.get("type", ""), duration_minutes=t.get("duration_minutes", 0), priority=t.get("priority", 1), earliest_time=t.get("earliest_time"), latest_time=t.get("latest_time"))
        pet = next((pp for pp in owner.pets if pp.id == pet_id), None)
        if pet:
            pet.add_task(task)

    return owner


def load_demo_fixture(path: str = "demo_fixture.json") -> Optional[Owner]:
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    return build_demo_owner_from_dict(data)


def print_schedule_table(owner: Owner, schedule):
    tasks = {t.id: t for t in owner.get_all_tasks()}
    rows = []
    for entry in schedule.get_today_tasks():
        start = entry.scheduled_start.strftime("%H:%M") if entry.scheduled_start else "--:--"
        end = entry.scheduled_end.strftime("%H:%M") if entry.scheduled_end else "--:--"
        task = tasks.get(entry.task_id)
        title = task.title if task else f"Task {entry.task_id}"
        pet_name = None
        if task:
            pid = task.pet_id
            pet = next((p for p in owner.pets if p.id == pid), None)
            pet_name = pet.name if pet else "Unknown"
        rows.append((start, end, title, pet_name, entry.status))

    # simple table print
    print(f"Today's Schedule for {owner.name} ({schedule.date}):\n")
    print(f"{'Start':<6} {'End':<6} {'Task':<30} {'Pet':<15} {'Status':<10}")
    print("-" * 75)
    for r in rows:
        print(f"{r[0]:<6} {r[1]:<6} {r[2]:<30} {r[3]:<15} {r[4]:<10}")
    print("\n", schedule.summarize())


def main():
    # Try to load demo fixture first
    owner = load_demo_fixture()
    if owner is None:
        # fallback: create a simple seeded demo
        owner = Owner(id=1, name="Alice", email="alice@example.com")
        owner.set_availability([
            {"start": time(8, 0), "end": time(12, 0)},
            {"start": time(14, 0), "end": time(18, 0)},
        ])

        pet1 = Pet(id=1, name="Buddy", species="Dog", age=4)
        pet2 = Pet(id=2, name="Milo", species="Cat", age=2)
        owner.add_pet(pet1)
        owner.add_pet(pet2)

        t1 = Task(id=1, pet_id=pet1.id, title="Morning Walk", type="walk", duration_minutes=30, priority=5,
                  earliest_time=time(8, 0), latest_time=time(10, 0), requires_walker=True)
        t2 = Task(id=2, pet_id=pet1.id, title="Feed Breakfast", type="feed", duration_minutes=10, priority=10,
                  earliest_time=time(7, 0), latest_time=time(9, 0))
        t3 = Task(id=3, pet_id=pet2.id, title="Give Medication", type="med", duration_minutes=5, priority=9,
                  earliest_time=time(8, 0), latest_time=time(20, 0))

        pet1.add_task(t1)
        pet1.add_task(t2)
        pet2.add_task(t3)

    # Run scheduler
    sched = Scheduler(date=date.today())
    sched.run_metadata["owner"] = owner
    try:
        schedule = sched.generate_plan()
    except Exception as e:
        print(f"Scheduling failed: {e}")
        return

    print_schedule_table(owner, schedule)


if __name__ == "__main__":
    main()
