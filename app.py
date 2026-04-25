import streamlit as st
from pawpal_system import Owner, Pet, Task, TaskInstance, Scheduler, Storage
from agent import PawPalAgent
from datetime import date, time
import os

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

# Attempt to load persisted owner data on startup
storage = Storage()
if "owner" not in st.session_state:
    try:
        loaded = storage.load_owner("data.json")
    except Exception:
        loaded = None
    if loaded:
        st.session_state["owner"] = loaded
    else:
        st.session_state["owner"] = Owner(name=owner_name)

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
    # persist owner -> data.json
    try:
        storage.save_owner(owner, "data.json")
    except Exception as e:
        st.warning(f"Could not save data: {e}")
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
    # attach human-friendly priority level as well
    task.priority_level = priority
    pet.add_task(task)
    # also keep UI-friendly task record in session_state for quick table view
    st.session_state.tasks.append({"title": task_title, "duration_minutes": int(duration), "priority": priority})
    # persist owner -> data.json
    try:
        storage.save_owner(owner, "data.json")
    except Exception as e:
        st.warning(f"Could not save data: {e}")
    st.success(f"Added task: {task_title} to {pet.name}")

if st.session_state.tasks:
    st.write("Current tasks:")
    for i, task in enumerate(st.session_state.tasks):
        col_a, col_b, col_c, col_d = st.columns([3, 1, 1, 1])
        with col_a:
            st.write(task["title"])
        with col_b:
            st.write(f"{task['duration_minutes']} min")
        with col_c:
            st.write(task["priority"])
        with col_d:
            if st.button("Delete", key=f"del_{i}"):
                owner = get_owner(owner_name)
                for p in owner.pets:
                    p.tasks = [t for t in p.tasks if not (
                        t.title == task["title"] and t.duration_minutes == task["duration_minutes"]
                    )]
                st.session_state.tasks.pop(i)
                try:
                    storage.save_owner(owner, "data.json")
                except Exception as e:
                    st.warning(f"Could not save: {e}")
                st.rerun()
else:
    st.info("No tasks yet. Add one above.")

# Save / Reset buttons
btn_save, btn_reset = st.columns(2)
with btn_save:
    if st.button("Save now", use_container_width=True):
        owner = get_owner(owner_name)
        try:
            try:
                backup_path = storage.backup_owner_file("data.json")
                st.info(f"Backup created: {backup_path}")
            except FileNotFoundError:
                pass
            storage.save_owner(owner, "data.json")
            st.success("Saved owner data to data.json")
        except Exception as e:
            st.error(f"Save failed: {e}")
with btn_reset:
    if st.button("Reset all data", type="secondary", use_container_width=True):
        if os.path.exists("data.json"):
            os.remove("data.json")
        st.session_state["owner"] = Owner(name=owner_name)
        st.session_state.tasks = []
        st.success("All data cleared.")
        st.rerun()

st.divider()

st.subheader("Build Schedule")
st.caption("This button should call your scheduling logic once you implement it.")

if st.button("Generate schedule"):
    owner = get_owner(owner_name)
    pet = find_or_create_pet(owner, pet_name, species)

    # Sync UI task list into the owner's pet tasks
    pri_map = {"low": 1, "medium": 2, "high": 3}
    ui_tasks = st.session_state.get("tasks", [])
    next_id = max((t.id or 0 for t in owner.get_all_tasks()), default=0) + 1
    for t in ui_tasks:
        exists = any(
            tt.title == t.get("title") and tt.duration_minutes == int(t.get("duration_minutes", 0))
            for tt in pet.get_tasks()
        )
        if exists:
            continue
        task = Task(
            id=next_id, pet_id=pet.id,
            title=t.get("title", ""),
            duration_minutes=int(t.get("duration_minutes", 0)),
            priority=pri_map.get(t.get("priority", "medium"), 2),
            priority_level=t.get("priority", "medium"),
        )
        pet.add_task(task)
        next_id += 1

    # Run PawPal Agent
    agent = PawPalAgent(owner)
    try:
        plan, decisions = agent.run(date.today())
    except Exception as e:
        st.error(f"Agent failed: {e}")
        plan = None
        decisions = []

    if plan is not None:
        n_scheduled = len([d for d in decisions if d.scheduled])
        st.success(f"Schedule generated — {n_scheduled} task(s) scheduled")
        st.markdown(plan.summarize())

        # Conflict detection
        sched = Scheduler(date=date.today())
        sched.run_metadata["owner"] = owner
        conflicts = sched.detect_conflicts(plan)
        if conflicts:
            id_to_title = {t.id: t.title for t in owner.get_all_tasks()}
            st.warning(f"{len(conflicts)} potential conflict(s) detected.")
            for a, b, reason in conflicts:
                ta = id_to_title.get(a.task_id, f"Task {a.task_id}")
                tb = id_to_title.get(b.task_id, f"Task {b.task_id}")
                st.warning(f"{reason}: '{ta}' and '{tb}'")

        # Schedule table
        sorted_entries = sched.sort_by_time(plan.get_today_tasks(), "scheduled_start")
        id_to_title = {t.id: t.title for t in owner.get_all_tasks()}
        id_to_priority = {t.id: getattr(t, "priority_level", "medium") for t in owner.get_all_tasks()}
        rows = []
        em = {"high": "🔴", "medium": "🟡", "low": "🟢"}
        for e in sorted_entries:
            plev = id_to_priority.get(e.task_id, "medium")
            rows.append({
                "title": f"{em.get(plev.lower(), '🟡')} {id_to_title.get(e.task_id, '(unknown)')}",
                "start": e.scheduled_start,
                "end": e.scheduled_end,
                "priority": plev.title(),
                "status": e.status,
            })

        if rows:
            color_map = {"high": "#ffd6d6", "medium": "#fff4cc", "low": "#ddffdd"}
            html = ["<table style='border-collapse:collapse;width:100%'><tr>"]
            for h in ["Task", "Start", "End", "Priority", "Status"]:
                html.append(f"<th style='text-align:left;padding:8px;border-bottom:1px solid #ddd'>{h}</th>")
            html.append("</tr>")
            for r in rows:
                p = (r.get("priority") or "medium").lower()
                bg = color_map.get(p, "#fff4cc")
                html.append(
                    f"<tr style='background:{bg}'>"
                    f"<td style='padding:8px;border-bottom:1px solid #eee'>{r['title']}</td>"
                    f"<td style='padding:8px;border-bottom:1px solid #eee'>{r['start'] or '--:--'}</td>"
                    f"<td style='padding:8px;border-bottom:1px solid #eee'>{r['end'] or '--:--'}</td>"
                    f"<td style='padding:8px;border-bottom:1px solid #eee'>{p.title()}</td>"
                    f"<td style='padding:8px;border-bottom:1px solid #eee'>{r['status']}</td>"
                    "</tr>"
                )
            html.append("</table>")
            st.markdown("".join(html), unsafe_allow_html=True)
        else:
            st.info("No tasks fit into availability for today.")

        # Agent reasoning panel
        with st.expander("Agent Reasoning", expanded=False):
            if decisions:
                st.markdown("**Per-task decisions:**")
                decision_rows = [
                    {
                        "Task": d.task.title,
                        "Status": "✓ Scheduled" if d.scheduled else "✗ Not scheduled",
                        "Score": f"{d.score:.2f}",
                        "Reason": d.reason,
                    }
                    for d in decisions
                ]
                st.dataframe(decision_rows, use_container_width=True)
            else:
                st.info("No tasks were evaluated.")

            st.markdown("**Reasoning trace:**")
            for line in agent.trace:
                st.text(line)
