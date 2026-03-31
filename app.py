import streamlit as st
from pawpal_system import Owner, Pet, Task, TaskInstance, Scheduler
from datetime import date, time

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")

st.title("🐾 PawPal+")

st.markdown(
    """
Welcome to the PawPal+ starter app.

This file is intentionally thin. It gives you a working Streamlit app so you can start quickly,
but **it does not implement the project logic**. Your job is to design the system and build it.

Use this app as your interactive demo once your backend classes/functions exist.
"""
)

with st.expander("Scenario", expanded=True):
    st.markdown(
        """
**PawPal+** is a pet care planning assistant. It helps a pet owner plan care tasks
for their pet(s) based on constraints like time, priority, and preferences.

You will design and implement the scheduling logic and connect it to this Streamlit UI.
"""
    )

with st.expander("What you need to build", expanded=True):
    st.markdown(
        """
At minimum, your system should:
- Represent pet care tasks (what needs to happen, how long it takes, priority)
- Represent the pet and the owner (basic info and preferences)
- Build a plan/schedule for a day that chooses and orders tasks based on constraints
- Explain the plan (why each task was chosen and when it happens)
"""
    )

st.divider()

st.subheader("Quick Demo Inputs (UI only)")
owner_name = st.text_input("Owner name", value="Jordan")
pet_name = st.text_input("Pet name", value="Mochi")
species = st.selectbox("Species", ["dog", "cat", "other"])

# Session helpers
def get_owner(name: str) -> Owner:
    o = st.session_state.get("owner")
    if not isinstance(o, Owner):
        st.session_state["owner"] = Owner(name=name)
    return st.session_state["owner"]


def find_or_create_pet(owner: Owner, name: str, species: str) -> Pet:
    for p in owner.pets:
        if p.name == name:
            return p
    pet = Pet(name=name, species=species)
    owner.add_pet(pet)
    return pet

# Add pet UI: call Owner.add_pet when user submits
if st.button("Add pet"):
    owner = get_owner(owner_name)
    pet = find_or_create_pet(owner, pet_name, species)
    st.success(f"Added pet: {pet.name}")

st.markdown("### Tasks")
st.caption("Add a few tasks. In your final version, these should feed into your scheduler.")

if "tasks" not in st.session_state:
    st.session_state.tasks = []

col1, col2, col3 = st.columns(3)
with col1:
    task_title = st.text_input("Task title", value="Morning walk")
with col2:
    duration = st.number_input("Duration (minutes)", min_value=1, max_value=240, value=20)
with col3:
    priority = st.selectbox("Priority", ["low", "medium", "high"], index=2)

if st.button("Add task"):
    owner = get_owner(owner_name)
    pet = find_or_create_pet(owner, pet_name, species)
    # create Task instance and attach to pet
    pri_map = {"low": 1, "medium": 2, "high": 3}
    next_id = max((t.id or 0 for t in owner.get_all_tasks()), default=0) + 1
    task = Task(id=next_id, pet_id=pet.id, title=task_title, duration_minutes=int(duration), priority=pri_map.get(priority, 2))
    pet.add_task(task)
    # also keep UI-friendly task record in session_state for quick table view
    st.session_state.tasks.append({"title": task_title, "duration_minutes": int(duration), "priority": priority})
    st.success(f"Added task: {task_title} to {pet.name}")

if st.session_state.tasks:
    st.write("Current tasks:")
    st.table(st.session_state.tasks)
else:
    st.info("No tasks yet. Add one above.")

st.divider()

st.subheader("Build Schedule")
st.caption("This button should call your scheduling logic once you implement it.")

if st.button("Generate schedule"):
    # Persist or retrieve Owner in session_state
    def get_owner(name: str) -> Owner:
        o = st.session_state.get("owner")
        if not isinstance(o, Owner):
            st.session_state["owner"] = Owner(name=name)
        return st.session_state["owner"]

    owner = get_owner(owner_name)

    # Ensure a Pet exists for the owner
    def find_or_create_pet(owner: Owner, name: str, species: str) -> Pet:
        for p in owner.pets:
            if p.name == name:
                return p
        pet = Pet(name=name, species=species)
        owner.add_pet(pet)
        return pet

    pet = find_or_create_pet(owner, pet_name, species)

    # Map UI tasks into Task objects attached to the pet
    pri_map = {"low": 1, "medium": 2, "high": 3}
    ui_tasks = st.session_state.get("tasks", [])
    next_id = max((t.id or 0 for t in owner.get_all_tasks()), default=0) + 1
    for t in ui_tasks:
        exists = any((tt.title == t.get("title") and tt.duration_minutes == int(t.get("duration_minutes", 0))) for tt in pet.get_tasks())
        if exists:
            continue
        task = Task(id=next_id, pet_id=pet.id, title=t.get("title", ""), duration_minutes=int(t.get("duration_minutes", 0)), priority=pri_map.get(t.get("priority", "medium"), 2))
        pet.add_task(task)
        next_id += 1

    # Provide a default availability window if none set
    if not owner.availability:
        owner.set_availability([{"start": time(8, 0), "end": time(20, 0)}])

    # Run scheduler
    sched = Scheduler(date=date.today())
    sched.run_metadata["owner"] = owner
    try:
        plan = sched.generate_plan()
    except Exception as e:
        st.error(f"Scheduling failed: {e}")
        plan = None

    if plan:
        st.success("Schedule generated")
        st.markdown(plan.summarize())

        # Detect conflicts and show lightweight warnings without crashing
        conflicts = sched.detect_conflicts(plan)
        if conflicts:
            st.warning(f"{len(conflicts)} potential conflict(s) detected. Review below.")
            id_to_title = {t.id: t.title for t in owner.get_all_tasks()}
            for a, b, reason in conflicts:
                title_a = id_to_title.get(a.task_id, f"Task {a.task_id}")
                title_b = id_to_title.get(b.task_id, f"Task {b.task_id}")
                start_a = a.scheduled_start or "(unscheduled)"
                start_b = b.scheduled_start or "(unscheduled)"
                st.warning(f"{reason}: '{title_a}' (task {a.task_id}) and '{title_b}' (task {b.task_id}) — starts {start_a} / {start_b}")

        # Present a sorted table (by scheduled_start) for clarity
        sorted_entries = sched.sort_by_time(plan.get_today_tasks(), "scheduled_start")
        id_to_title = {t.id: t.title for t in owner.get_all_tasks()}
        rows = []
        for e in sorted_entries:
            rows.append({
                "task_id": e.task_id,
                "title": id_to_title.get(e.task_id, "(unknown)"),
                "start": e.scheduled_start,
                "end": e.scheduled_end,
                "status": e.status,
            })

        if rows:
            st.table(rows)
        else:
            st.info("No tasks fit into availability for today.")
