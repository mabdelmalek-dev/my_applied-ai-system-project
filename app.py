import streamlit as st
from pawpal_system import Owner, Pet, Task, Storage
from agent import (
    build_daily_schedule,
    build_daily_plan,
    validate_tasks,
    rank_tasks,
    explain_plan,
)
from metrics import evaluate_plan, run_benchmarks
from datetime import date, time
import os

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")
st.title("🐾 PawPal+")
st.caption("AI-powered pet care planner — tell the app your day and it builds the best schedule for your pet.")

# ── Storage / session state ───────────────────────────────────────────────────
storage = Storage()
if "owner" not in st.session_state:
    try:
        loaded = storage.load_owner("data.json")
    except Exception:
        loaded = None
    st.session_state["owner"] = loaded if loaded else Owner(name="Jordan")

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


st.divider()

# ── Step 1: Your available window ─────────────────────────────────────────────
st.subheader("1. Your Available Window")
st.caption("Tell the app when you are free today. It will only schedule tasks within this window.")

col_ws, col_we = st.columns(2)
with col_ws:
    window_start = st.time_input("Available from", value=time(8, 0))
with col_we:
    window_end = st.time_input("Available until", value=time(12, 0))

total_window_min = (window_end.hour * 60 + window_end.minute) - (window_start.hour * 60 + window_start.minute)
if total_window_min > 0:
    h, m = divmod(total_window_min, 60)
    st.info(f"Window: {window_start.strftime('%I:%M %p')} – {window_end.strftime('%I:%M %p')}  ({h}h {m}m available)")
else:
    st.error("End time must be after start time.")

st.divider()

# ── Step 2: Owner & Pet ───────────────────────────────────────────────────────
st.subheader("2. Owner & Pet")
col_o, col_p, col_s = st.columns(3)
with col_o:
    owner_name = st.text_input("Owner name", value="Jordan")
with col_p:
    pet_name = st.text_input("Pet name", value="Mochi")
with col_s:
    species = st.selectbox("Species", ["dog", "cat", "other"])

if st.button("Save owner / pet"):
    owner = get_owner(owner_name)
    find_or_create_pet(owner, pet_name, species)
    try:
        storage.save_owner(owner, "data.json")
        st.success(f"Saved — owner: {owner_name}, pet: {pet_name}")
    except Exception as e:
        st.warning(f"Could not save: {e}")

st.divider()

# ── Step 3: Tasks ─────────────────────────────────────────────────────────────
st.subheader("3. Tasks")
st.caption(
    "Add each care task. For strict tasks (e.g. medicine at exactly 9:00 AM) "
    "enable **Fixed start time** — otherwise the app picks the best slot automatically."
)

col1, col2, col3 = st.columns([3, 1, 1])
with col1:
    task_title = st.text_input("Task name", value="Walk dog")
with col2:
    duration = st.number_input("Duration (min)", min_value=1, max_value=240, value=30)
with col3:
    priority = st.selectbox("Priority", ["low", "medium", "high"], index=1)

col4, col5 = st.columns([2, 2])
with col4:
    preferred_time = st.selectbox(
        "Preferred time of day",
        ["morning", "afternoon", "evening", "anytime"],
        index=0,
        help="The app tries to place the task in this part of the day.",
    )
with col5:
    use_fixed = st.checkbox("Fixed start time (must happen at exact time)")
    fixed_start = None
    if use_fixed:
        fixed_t = st.time_input("Fixed start time", value=time(9, 0))
        fixed_start = f"{fixed_t.hour:02d}:{fixed_t.minute:02d}"

if st.button("Add task", type="primary"):
    if not task_title.strip():
        st.error("Task name cannot be empty.")
    elif duration <= 0:
        st.error("Duration must be greater than 0.")
    else:
        owner = get_owner(owner_name)
        pet = find_or_create_pet(owner, pet_name, species)
        pri_map = {"low": 1, "medium": 2, "high": 3}
        next_id = max((t.id or 0 for t in owner.get_all_tasks()), default=0) + 1
        task_obj = Task(
            id=next_id, pet_id=pet.id,
            title=task_title.strip(),
            duration_minutes=int(duration),
            priority=pri_map.get(priority, 2),
            priority_level=priority,
        )
        pet.add_task(task_obj)
        st.session_state.tasks.append({
            "title": task_title.strip(),
            "duration_minutes": int(duration),
            "priority": priority,
            "preferred_time": preferred_time if preferred_time != "anytime" else None,
            "fixed_start_time": fixed_start,
            "pet": pet_name,
        })
        try:
            storage.save_owner(owner, "data.json")
        except Exception as e:
            st.warning(f"Could not save: {e}")
        label = f"fixed at {fixed_start}" if fixed_start else f"{preferred_time}"
        st.success(f"Added: {task_title} — {priority} priority, {duration} min, {label}")

# Task list
if st.session_state.tasks:
    st.write("**Your tasks:**")
    hdr = st.columns([3, 1, 1, 1, 1, 1])
    for col, label in zip(hdr, ["Task", "Min", "Priority", "Preferred", "Fixed at", ""]):
        col.markdown(f"**{label}**")

    for i, task in enumerate(st.session_state.tasks):
        ca, cb, cc, cd, ce, cf = st.columns([3, 1, 1, 1, 1, 1])
        with ca:
            st.write(task["title"])
        with cb:
            st.write(f"{task['duration_minutes']}")
        with cc:
            st.write(task["priority"])
        with cd:
            st.write(task.get("preferred_time") or "any")
        with ce:
            st.write(task.get("fixed_start_time") or "—")
        with cf:
            if st.button("✕", key=f"del_{i}"):
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

# ── Step 4: Generate Schedule ─────────────────────────────────────────────────
st.subheader("4. Generate My Schedule")

if st.button("Generate schedule", type="primary"):
    tasks = st.session_state.tasks

    if not tasks:
        st.warning("Add at least one task first.")
    elif total_window_min <= 0:
        st.error("Fix the available window before generating a schedule.")
    else:
        scheduled, unscheduled = build_daily_schedule(window_start, window_end, tasks)

        # ── Validate step ──────────────────────────────────────────────────
        valid = validate_tasks(tasks)
        with st.expander("Step 1 — Validate tasks", expanded=True):
            st.write(f"**{len(valid)}** valid task(s) out of {len(tasks)} submitted.")
            bad = len(tasks) - len(valid)
            if bad:
                st.warning(f"{bad} task(s) skipped (empty name or zero duration).")

        # ── Rank step ──────────────────────────────────────────────────────
        flexible = [t for t in valid if not t.get("fixed_start_time")]
        ranked = rank_tasks(flexible)
        with st.expander("Step 2 — Rank flexible tasks by score", expanded=True):
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
            fixed_count = len([t for t in valid if t.get("fixed_start_time")])
            if fixed_count:
                st.info(f"{fixed_count} task(s) are fixed-time and skipped scoring.")
            if rank_rows:
                st.dataframe(rank_rows, use_container_width=True, hide_index=True)

        # ── Schedule step ──────────────────────────────────────────────────
        with st.expander("Step 3 — Place tasks into time slots", expanded=True):
            total_used = sum(t["duration_minutes"] for t in scheduled)
            st.write(
                f"**{len(scheduled)}** task(s) placed using **{total_used} min** "
                f"of **{total_window_min} min** available."
            )
            if unscheduled:
                st.warning(
                    f"{len(unscheduled)} task(s) could not be placed: "
                    + ", ".join(t["title"] for t in unscheduled)
                )

        # ── Explain step ───────────────────────────────────────────────────
        with st.expander("Step 4 — Explain decisions", expanded=True):
            for entry in scheduled:
                icon = "📌" if entry["fixed"] else "✅"
                st.markdown(f"{icon} {entry['explanation']}")
            for t in unscheduled:
                st.markdown(f"❌ **{t['title']}** — {t['reason']}")

        # ── Final time-slotted schedule ────────────────────────────────────
        st.divider()
        st.markdown("### Your Daily Schedule")
        if scheduled:
            color_map = {"high": "#ffd6d6", "medium": "#fff4cc", "low": "#ddffdd"}
            pin_color = "#e8f0ff"
            html = [
                "<table style='border-collapse:collapse;width:100%'>",
                "<tr>",
                *[
                    f"<th style='text-align:left;padding:10px 8px;border-bottom:2px solid #ccc;"
                    f"background:#f5f5f5'>{h}</th>"
                    for h in ["Time", "Task", "Duration", "Priority", "Explanation"]
                ],
                "</tr>",
            ]
            for entry in scheduled:
                p = entry["priority"]
                bg = pin_color if entry["fixed"] else color_map.get(p, "#fff4cc")
                icon = em.get(p, "🟡")
                pin = "📌 " if entry["fixed"] else ""
                html.append(
                    f"<tr style='background:{bg}'>"
                    f"<td style='padding:10px 8px;border-bottom:1px solid #eee;"
                    f"font-weight:bold;white-space:nowrap'>{entry['start_fmt']} – {entry['end_fmt']}</td>"
                    f"<td style='padding:10px 8px;border-bottom:1px solid #eee'>{pin}{icon} {entry['title']}</td>"
                    f"<td style='padding:10px 8px;border-bottom:1px solid #eee'>{entry['duration_minutes']} min</td>"
                    f"<td style='padding:10px 8px;border-bottom:1px solid #eee'>{p.title()}</td>"
                    f"<td style='padding:10px 8px;border-bottom:1px solid #eee;"
                    f"font-style:italic;color:#555'>{entry['explanation']}</td>"
                    "</tr>"
                )
            html.append("</table>")
            st.markdown("".join(html), unsafe_allow_html=True)

            if unscheduled:
                st.markdown("**Not scheduled:**")
                for t in unscheduled:
                    st.markdown(f"- ❌ **{t['title']}**: {t['reason']}")
        else:
            st.info("No tasks could be placed in the selected window.")

        # ── Performance metrics ────────────────────────────────────────────
        flat_scheduled = [{"title": e["title"], "duration_minutes": e["duration_minutes"],
                           "priority": e["priority"]} for e in scheduled]
        metrics = evaluate_plan(tasks, flat_scheduled, total_window_min)
        st.divider()
        st.markdown("### AI Performance Metrics")
        m1, m2, m3, m4 = st.columns(4)

        def _pct(v):
            return f"{v * 100:.1f}%"

        m1.metric("Task Coverage",       _pct(metrics["task_coverage"]),
                  help="% of valid tasks that were scheduled")
        m2.metric("Time Efficiency",     _pct(metrics["time_efficiency"]),
                  help="% of available window used")
        m3.metric("Priority Compliance", _pct(metrics["priority_compliance"]),
                  help="No higher-priority task dropped while a lower one was kept")
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
            c1.metric("Coverage",   f"{m['task_coverage']*100:.0f}%")
            c2.metric("Efficiency", f"{m['time_efficiency']*100:.0f}%")
            c3.metric("Compliance", f"{m['priority_compliance']*100:.0f}%")
            c4.metric("Overall",    f"{m['overall_score']*100:.0f}%")
