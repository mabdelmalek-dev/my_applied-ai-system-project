from datetime import date, time
from pawpal_system import Owner, Pet, Task, Scheduler


def main():
    # Create owner and availability
    owner = Owner(id=1, name="Alice", email="alice@example.com")
    owner.set_availability([
        {"start": time(8, 0), "end": time(12, 0)},
        {"start": time(14, 0), "end": time(18, 0)},
    ])

    # Create pets
    pet1 = Pet(id=1, name="Buddy", species="Dog", age=4)
    pet2 = Pet(id=2, name="Milo", species="Cat", age=2)
    owner.add_pet(pet1)
    owner.add_pet(pet2)

    # Create tasks
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
    schedule = sched.generate_plan()

    # Map task ids to titles for printing
    tasks = {t.id: t for t in owner.get_all_tasks()}

    print(f"Today's Schedule for {owner.name} ({schedule.date}):\n")
    for entry in schedule.get_today_tasks():
        start = entry.scheduled_start.strftime("%H:%M") if entry.scheduled_start else "--:--"
        end = entry.scheduled_end.strftime("%H:%M") if entry.scheduled_end else "--:--"
        task_title = tasks.get(entry.task_id).title if tasks.get(entry.task_id) else f"Task {entry.task_id}"
        pet_name = None
        if tasks.get(entry.task_id):
            pid = tasks.get(entry.task_id).pet_id
            pet = next((p for p in owner.pets if p.id == pid), None)
            pet_name = pet.name if pet else "Unknown"
        print(f"- {start} - {end}: {task_title} ({pet_name})")

    print("\n", schedule.summarize())


if __name__ == "__main__":
    main()
