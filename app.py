import streamlit as st
from pawpal_system import Owner, Pet, Task, Storage
from agent import build_daily_plan, validate_tasks, rank_tasks, schedule_tasks, explain_plan
from metrics import evaluate_plan, run_benchmarks
from datetime import date, time
import os

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")
st.title("🐾 PawPal+")
st.caption("AI-powered pet care planner — enter your tasks and let the agent build the best daily schedule.")

st.divider()

# ── Owner / Pet inputs ────────────────────────────────────────────────────────
st.subheader("Owner & Pet")
col_o, col_p, col_s = st.columns(3)
with col_o:
    owner_name = st.text_input("Owner name", value="Jordan")
with col_p:
    pet_name = st.text_input("Pet name", value="Mochi")
with col_s:
    species = st.selectbox("Species", ["dog", "cat", "other"])

# Storage + session state
storage = Storage()
if "owner" not in st.session_state:
    try:
        loaded = storage.load_owner("data.json")
    except Exception:
        loaded = None
    st.session_state["owner"] = loaded if loaded else Owner(name=owner_name)

if "tasks" not in st.session_state:
    st.session_state.tasks = []


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


if st.button("Save owner / pet"):
    owner = get_owner(owner_name)
    find_or_create_pet(owner, pet_name, species)
    try:
        storage.save_owner(owner, "data.json")
        st.success(f"Saved — owner: {owner_name}, pet: {pet_name}")
    except Exception as e:
        st.warning(f"Could not save: {e}")

st.divider()

# ── Task inputs ───────────────────────────────────────────────────────────────
st.subheader("Tasks")
st.caption("Each task is an AI decision factor: title, duration, priority, and preferred time of day.")

col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
with col1:
    task_title = st.text_input("Task title", value="Morning walk")
with col2:
    duration = st.number_input("Duration (min)", min_value=1, max_value=240, value=30)
with col3:
    priority = st.selectbox("Priority", ["low", "medium", "high"], index=2)
with col4:
    preferred_time = st.selectbox("Preferred time", ["morning", "afternoon", "evening", "any"], index=0)

if st.button("Add task"):
    owner = get_owner(owner_name)
    pet = find_or_create_pet(owner, pet_name, species)
    pri_map = {"low": 1, "medium": 2, "high": 3}
    next_id = max((t.id or 0 for t in owner.get_all_tasks()), default=0) + 1
    task_obj = Task(
        id=next_id, pet_id=pet.id,
        title=task_title,
        duration_minutes=int(duration),
        priority=pri_map.get(priority, 2),
        priority_level=priority,
    )
    pet.add_task(task_obj)
    st.session_state.tasks.append({
        "title": task_title,
        "duration_minutes": int(duration),
        "priority": priority,
        "preferred_time": preferred_time if preferred_time != "any" else None,
        "pet": pet_name,
    })
    try:
        storage.save_owner(owner, "data.json")
    except Exception as e:
        st.warning(f"Could not save: {e}")
    st.success(f"Added: {task_title} ({priority} priority, {duration} min, {preferred_time})")

# Task list with delete
if st.session_state.tasks:
    st.write("**Current tasks:**")
    for i, task in enumerate(st.session_state.tasks):
        ca, cb, cc, cd, ce = st.columns([3, 1, 1, 1, 1])
        with ca:
            st.write(task["title"])
        with cb:
            st.write(f"{task['duration_minutes']} min")
        with cc:
            st.write(task["priority"])
        with cd:
            st.write(task.get("preferred_time") or "any")
        with ce:
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

# Save / Reset
btn_save, btn_reset = st.columns(2)
with btn_save:
    if st.button("Save now", use_container_width=True):
        owner = get_owner(owner_name)
        try:
            try:
                backup_path = storage.backup_owner_file("data.json")
                st.info(f"Backup: {backup_path}")
            except FileNotFoundError:
                pass
            storage.save_owner(owner, "data.json")
            st.success("Saved to data.json")
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

# ── Generate Schedule ─────────────────────────────────────────────────────────
st.subheader("Build Schedule")
available_minutes = st.number_input(
    "Available time today (minutes)", min_value=30, max_value=1440, value=480, step=30
)

if st.button("Generate schedule", type="primary"):
    tasks = st.session_state.tasks

    if not tasks:
        st.warning("Add at least one task before generating a schedule.")
    else:
        owner = get_owner(owner_name)
        pet = find_or_create_pet(owner, pet_name, species)

        # ── Step 1: Validate ──────────────────────────────────────────────
        valid = validate_tasks(tasks)
        invalid = [t for t in tasks if t not in valid]

        with st.expander("Step 1 — Validate tasks", expanded=True):
            st.write(f"**{len(valid)}** valid task(s) out of {len(tasks)} submitted.")
            if invalid:
                st.warning(f"{len(invalid)} task(s) skipped (missing title or zero duration).")

        # ── Step 2: Rank ──────────────────────────────────────────────────
        ranked = rank_tasks(valid, owner, pet)

        with st.expander("Step 2 — Rank by priority & preferences", expanded=True):
            st.write("Tasks sorted by score (highest first):")
            em = {"high": "🔴", "medium": "🟡", "low": "🟢"}
            rank_rows = [
                {
                    "Rank": i + 1,
                    "Task": t["title"],
                    "Priority": t.get("priority", "medium"),
                    "Preferred time": t.get("preferred_time") or "any",
                    "Score": t["_score"],
                }
                for i, t in enumerate(ranked)
            ]
            st.dataframe(rank_rows, use_container_width=True, hide_index=True)

        # ── Step 3: Schedule ──────────────────────────────────────────────
        scheduled = schedule_tasks(ranked, available_minutes)
        not_scheduled = [t for t in ranked if t["title"] not in {s["title"] for s in scheduled}]
        total_used = sum(t["duration_minutes"] for t in scheduled)

        with st.expander("Step 3 — Build daily schedule", expanded=True):
            st.write(
                f"**{len(scheduled)}** task(s) scheduled using **{total_used}** of "
                f"**{available_minutes}** available minutes."
            )
            if not_scheduled:
                st.warning(
                    f"{len(not_scheduled)} task(s) didn't fit: "
                    + ", ".join(t["title"] for t in not_scheduled)
                )

        # ── Step 4: Explain ───────────────────────────────────────────────
        explanations = explain_plan(scheduled)

        with st.expander("Step 4 — Explain decisions", expanded=True):
            for explanation in explanations:
                st.markdown(f"✅ {explanation}")
            if not_scheduled:
                for t in not_scheduled:
                    total_needed = sum(x["duration_minutes"] for x in ranked)
                    st.markdown(
                        f"❌ **{t['title']}** was not scheduled because there was not enough "
                        f"time remaining (needs {t['duration_minutes']} min)."
                    )

        # ── Final schedule table ──────────────────────────────────────────
        st.divider()
        st.markdown("### Final Schedule")
        if scheduled:
            color_map = {"high": "#ffd6d6", "medium": "#fff4cc", "low": "#ddffdd"}
            em = {"high": "🔴", "medium": "🟡", "low": "🟢"}
            html = [
                "<table style='border-collapse:collapse;width:100%'><tr>",
                *[
                    f"<th style='text-align:left;padding:8px;border-bottom:2px solid #ccc'>{h}</th>"
                    for h in ["#", "Task", "Duration", "Priority", "Preferred time", "Explanation"]
                ],
                "</tr>",
            ]
            for i, (task, explanation) in enumerate(zip(scheduled, explanations), start=1):
                p = (task.get("priority") or "medium").lower()
                bg = color_map.get(p, "#fff4cc")
                icon = em.get(p, "🟡")
                pt = task.get("preferred_time") or "any"
                html.append(
                    f"<tr style='background:{bg}'>"
                    f"<td style='padding:8px;border-bottom:1px solid #eee'>{i}</td>"
                    f"<td style='padding:8px;border-bottom:1px solid #eee'>{icon} {task['title']}</td>"
                    f"<td style='padding:8px;border-bottom:1px solid #eee'>{task['duration_minutes']} min</td>"
                    f"<td style='padding:8px;border-bottom:1px solid #eee'>{p.title()}</td>"
                    f"<td style='padding:8px;border-bottom:1px solid #eee'>{pt}</td>"
                    f"<td style='padding:8px;border-bottom:1px solid #eee;font-style:italic'>{explanation}</td>"
                    "</tr>"
                )
            html.append("</table>")
            st.markdown("".join(html), unsafe_allow_html=True)
        else:
            st.info("No tasks could be scheduled within the available time.")

        # ── Performance metrics ───────────────────────────────────────────
        st.divider()
        st.markdown("### AI Performance Metrics")
        st.caption("How well did the planner perform on this plan?")
        metrics = evaluate_plan(tasks, scheduled, available_minutes)

        m1, m2, m3, m4 = st.columns(4)
        def _pct(v): return f"{v * 100:.1f}%"
        def _color(v): return "green" if v >= 0.8 else "orange" if v >= 0.5 else "red"

        m1.metric("Task Coverage",       _pct(metrics["task_coverage"]),
                  help="% of valid tasks that were scheduled")
        m2.metric("Time Efficiency",     _pct(metrics["time_efficiency"]),
                  help="% of available time used")
        m3.metric("Priority Compliance", _pct(metrics["priority_compliance"]),
                  help="No high-priority task left out while a lower one was included")
        m4.metric("Overall Score",       _pct(metrics["overall_score"]),
                  help="Average of the three metrics above")

st.divider()

# ── Benchmark Tests ───────────────────────────────────────────────────────────
st.subheader("AI Reliability — Benchmark Tests")
st.caption("Run predefined scenarios to verify the planner always makes correct decisions.")

if st.button("Run benchmark tests"):
    results = run_benchmarks()
    n_pass = sum(1 for r in results if r["passed"])
    n_fail = len(results) - n_pass

    if n_fail == 0:
        st.success(f"All {n_pass} benchmarks passed!")
    else:
        st.error(f"{n_fail} benchmark(s) failed, {n_pass} passed.")

    for r in results:
        icon = "✅" if r["passed"] else "❌"
        with st.expander(f"{icon} {r['name']}", expanded=not r["passed"]):
            if r["failures"]:
                for f in r["failures"]:
                    st.error(f)
            else:
                st.write(f"Scheduled: {', '.join(r['scheduled_titles']) or '(none)'}")
            m = r["metrics"]
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Coverage",    f"{m['task_coverage']*100:.0f}%")
            c2.metric("Efficiency",  f"{m['time_efficiency']*100:.0f}%")
            c3.metric("Compliance",  f"{m['priority_compliance']*100:.0f}%")
            c4.metric("Overall",     f"{m['overall_score']*100:.0f}%")
