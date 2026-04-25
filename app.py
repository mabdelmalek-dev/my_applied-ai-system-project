import json
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
from collections import defaultdict
import os
import re as _re


# ── Persistence helpers ───────────────────────────────────────────────────────

_OWNERS_DB = "owners_db.json"


def _load_owners_db() -> dict:
    """Return {owner_name: {"pets": [...], "tasks": [...]}} from owners_db.json."""
    if os.path.exists(_OWNERS_DB):
        try:
            with open(_OWNERS_DB, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def _save_owner_to_db(
    owner_name: str,
    pets: list,
    tasks: list,
    ws_label: str = "8:00 AM",
    we_label: str = "12:00 PM",
) -> None:
    """Upsert one owner's full profile (window, pets, tasks) into owners_db.json."""
    db = _load_owners_db()
    db[owner_name] = {
        "pets": list(pets),
        "tasks": list(tasks),
        "ws_label": ws_label,
        "we_label": we_label,
    }
    tmp = _OWNERS_DB + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(db, f, indent=2)
    os.replace(tmp, _OWNERS_DB)
    if "owners_db" in st.session_state:
        st.session_state.owners_db[owner_name] = db[owner_name]


def _delete_owner_from_db(owner_name: str) -> None:
    """Remove an owner entry from owners_db.json."""
    db = _load_owners_db()
    db.pop(owner_name, None)
    with open(_OWNERS_DB, "w", encoding="utf-8") as f:
        json.dump(db, f, indent=2)
    if "owners_db" in st.session_state:
        st.session_state.owners_db.pop(owner_name, None)


# ── Time helpers ──────────────────────────────────────────────────────────────

def _time_options(step_minutes: int = 30):
    opts = []
    for total in range(0, 24 * 60, step_minutes):
        h, m = divmod(total, 60)
        ampm = "AM" if h < 12 else "PM"
        h12 = h % 12 or 12
        opts.append(f"{h12}:{m:02d} {ampm}")
    return opts


def _parse_ampm(s: str) -> time:
    m = _re.match(r"(\d+):(\d+)\s*(AM|PM)", s.strip().upper())
    if not m:
        return time(8, 0)
    h, mn, ampm = int(m.group(1)), int(m.group(2)), m.group(3)
    if ampm == "PM" and h != 12:
        h += 12
    if ampm == "AM" and h == 12:
        h = 0
    return time(h, mn)


_TIME_OPTS = _time_options(30)

# ── Page config ───────────────────────────────────────────────────────────────

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")
st.title("🐾 PawPal+")
st.caption("AI-powered pet care planner — tell the app your day and it builds the best schedule for your pets.")

st.markdown("""
<style>
/* Prevent page-level horizontal scroll */
html, body { overflow-x: hidden; }
.main .block-container {
    max-width: 1300px !important;
    padding-left: 1rem !important;
    padding-right: 1rem !important;
    padding-top: 1rem;
}

/* Side emoji decorations */
.pawpal-deco {
    position: fixed; top: 0; bottom: 0;
    width: calc(50vw - 660px);
}
.pawpal-deco-left  { left: 0; }
.pawpal-deco-right { right: 0; }
    pointer-events: none; z-index: 0;
    user-select: none; overflow: hidden;
}
.pawpal-deco-left  { left: 0; }
.pawpal-deco-right { right: 0; }
.pawpal-deco span  { position: absolute; line-height: 1; }
</style>

<div class="pawpal-deco pawpal-deco-left">
  <span style="top:2%;  left:15%; font-size:5.5rem;opacity:0.20;transform:rotate(-12deg)">🐕</span>
  <span style="top:10%; left:55%; font-size:4.5rem;opacity:0.16;transform:rotate(8deg)">🐾</span>
  <span style="top:19%; left:22%; font-size:6rem;  opacity:0.18;transform:rotate(-5deg)">🐈</span>
  <span style="top:28%; left:60%; font-size:5rem;  opacity:0.15;transform:rotate(15deg)">🦮</span>
  <span style="top:37%; left:8%;  font-size:5.5rem;opacity:0.20;transform:rotate(-10deg)">🐩</span>
  <span style="top:46%; left:50%; font-size:6rem;  opacity:0.17;transform:rotate(7deg)">🐕‍🦺</span>
  <span style="top:55%; left:18%; font-size:5rem;  opacity:0.19;transform:rotate(-8deg)">🐶</span>
  <span style="top:63%; left:58%; font-size:5.5rem;opacity:0.15;transform:rotate(12deg)">🐱</span>
  <span style="top:72%; left:10%; font-size:6rem;  opacity:0.18;transform:rotate(-14deg)">🐈‍⬛</span>
  <span style="top:81%; left:48%; font-size:5rem;  opacity:0.16;transform:rotate(6deg)">🐾</span>
  <span style="top:89%; left:22%; font-size:5.5rem;opacity:0.20;transform:rotate(-9deg)">🐕</span>
  <span style="top:96%; left:55%; font-size:4.5rem;opacity:0.15;transform:rotate(11deg)">🦮</span>
</div>
<div class="pawpal-deco pawpal-deco-right">
  <span style="top:3%;  left:35%; font-size:5.5rem;opacity:0.18;transform:rotate(10deg)">🐈‍⬛</span>
  <span style="top:11%; left:8%;  font-size:6rem;  opacity:0.20;transform:rotate(-7deg)">🐕</span>
  <span style="top:20%; left:50%; font-size:5rem;  opacity:0.16;transform:rotate(13deg)">🐾</span>
  <span style="top:29%; left:18%; font-size:5.5rem;opacity:0.19;transform:rotate(-11deg)">🐶</span>
  <span style="top:38%; left:55%; font-size:6rem;  opacity:0.15;transform:rotate(6deg)">🦮</span>
  <span style="top:47%; left:10%; font-size:5rem;  opacity:0.20;transform:rotate(-9deg)">🐩</span>
  <span style="top:56%; left:45%; font-size:5.5rem;opacity:0.17;transform:rotate(14deg)">🐈</span>
  <span style="top:64%; left:20%; font-size:6rem;  opacity:0.18;transform:rotate(-6deg)">🐕‍🦺</span>
  <span style="top:73%; left:52%; font-size:5rem;  opacity:0.16;transform:rotate(9deg)">🐱</span>
  <span style="top:82%; left:12%; font-size:5.5rem;opacity:0.20;transform:rotate(-13deg)">🐕</span>
  <span style="top:90%; left:42%; font-size:6rem;  opacity:0.15;transform:rotate(7deg)">🐾</span>
  <span style="top:97%; left:18%; font-size:4.5rem;opacity:0.18;transform:rotate(-10deg)">🐈‍⬛</span>
</div>
""", unsafe_allow_html=True)

# ── Session state init ────────────────────────────────────────────────────────

if "owners_db" not in st.session_state:
    st.session_state.owners_db = _load_owners_db()

if "tasks" not in st.session_state:
    st.session_state.tasks = []

if "pets" not in st.session_state:
    st.session_state.pets = []

# No owner is selected on every fresh page load
if "active_owner_name" not in st.session_state:
    st.session_state.active_owner_name = ""

if "creating_new_owner" not in st.session_state:
    st.session_state.creating_new_owner = False

if "ws_label" not in st.session_state:
    st.session_state.ws_label = "8:00 AM"
if "we_label" not in st.session_state:
    st.session_state.we_label = "12:00 PM"

if "owner" not in st.session_state:
    st.session_state["owner"] = Owner(name="")


def get_owner(name: str) -> Owner:
    o = st.session_state.get("owner")
    if not isinstance(o, Owner) or o.name != name:
        st.session_state["owner"] = Owner(name=name)
    return st.session_state["owner"]


def find_or_create_pet(owner: Owner, name: str, species: str) -> Pet:
    for p in owner.pets:
        if p.name == name:
            return p
    pet = Pet(name=name, species=species)
    owner.add_pet(pet)
    return pet


_species_icons = {"dog": "🐕", "cat": "🐈", "other": "🐾"}
_em = {"high": "🔴", "medium": "🟡", "low": "🟢"}

# Default window values (overwritten inside the owner tab when an owner is active)
window_start = _parse_ampm(st.session_state.ws_label)
window_end   = _parse_ampm(st.session_state.we_label)
total_window_min = (window_end.hour * 60 + window_end.minute) - (window_start.hour * 60 + window_start.minute)

# ── Red tab styling ───────────────────────────────────────────────────────────
st.markdown("""
<style>
/* Tab strip */
.stTabs [data-baseweb="tab-list"] {
    gap: 6px;
    border-bottom: 3px solid #c0392b;
    padding-bottom: 0;
}
/* Every tab button */
.stTabs [data-baseweb="tab"] {
    background: #fff0f0;
    border: 2px solid #e74c3c;
    border-bottom: none;
    border-radius: 8px 8px 0 0;
    color: #c0392b;
    font-weight: 700;
    font-size: 0.92rem;
    padding: 8px 18px;
    transition: background 0.15s, color 0.15s;
}
/* Active tab */
.stTabs [aria-selected="true"] {
    background: #c0392b !important;
    color: #ffffff !important;
    border-color: #c0392b !important;
}
/* Hover on inactive */
.stTabs [data-baseweb="tab"]:hover {
    background: #e74c3c !important;
    color: #ffffff !important;
}
/* Hide the default underline indicator */
.stTabs [data-baseweb="tab-highlight"] { background: transparent !important; }
.stTabs [data-baseweb="tab-border"]    { display: none !important; }
</style>
""", unsafe_allow_html=True)

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs([
    "🐾  Owner & Pets",
    "📋  Tasks",
    "📅  Generate Schedule",
    "🧪  AI Reliability",
])

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — Owner & Pets
# ══════════════════════════════════════════════════════════════════════════════
with tab1:
    known_owners = sorted(st.session_state.owners_db.keys())
    _PLACEHOLDER = "— select owner —"
    owner_choices = [_PLACEHOLDER] + known_owners

    _sel_idx = (
        owner_choices.index(st.session_state.active_owner_name)
        if st.session_state.active_owner_name in owner_choices
        else 0
    )

    oc1, oc2 = st.columns([4, 1])
    with oc1:
        owner_choice = st.selectbox("Owner", owner_choices, index=_sel_idx)
    with oc2:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("+ New owner", use_container_width=True):
            st.session_state.creating_new_owner = True
            st.rerun()

    # Auto-load on dropdown change
    if owner_choice != _PLACEHOLDER and owner_choice != st.session_state.active_owner_name:
        data = st.session_state.owners_db.get(owner_choice, {})
        st.session_state.pets   = list(data.get("pets", []))
        st.session_state.tasks  = list(data.get("tasks", []))
        st.session_state.ws_label = data.get("ws_label", "8:00 AM")
        st.session_state.we_label = data.get("we_label", "12:00 PM")
        st.session_state.active_owner_name = owner_choice
        st.session_state["owner"] = Owner(name=owner_choice)
        st.session_state.creating_new_owner = False
        st.rerun()

    owner_name = st.session_state.active_owner_name

    if owner_choice == _PLACEHOLDER and not st.session_state.creating_new_owner:
        st.info("Select a saved owner from the list, or click **+ New owner** to start a new profile.")

    # New-owner form
    if st.session_state.creating_new_owner:
        st.markdown("**Create new owner profile**")
        with st.form("new_owner_form", clear_on_submit=True):
            new_name_input = st.text_input("Owner name", placeholder="Enter your name")
            nf1, nf2 = st.columns(2)
            with nf1:
                create_sub = st.form_submit_button("Create", use_container_width=True, type="primary")
            with nf2:
                cancel_sub = st.form_submit_button("Cancel", use_container_width=True)
        if cancel_sub:
            st.session_state.creating_new_owner = False
            st.rerun()
        if create_sub:
            nname = new_name_input.strip()
            if not nname:
                st.error("Name cannot be empty.")
            elif nname in st.session_state.owners_db:
                st.warning(f"'{nname}' already exists — select it from the dropdown.")
            else:
                st.session_state.pets  = []
                st.session_state.tasks = []
                st.session_state.active_owner_name = nname
                st.session_state["owner"] = Owner(name=nname)
                st.session_state.creating_new_owner = False
                _save_owner_to_db(nname, [], [], st.session_state.ws_label, st.session_state.we_label)
                st.rerun()

    # Window + Pets (only when owner is active)
    if owner_name:
        st.markdown("**Available window today:**")
        col_ws, col_we = st.columns(2)
        with col_ws:
            ws_label = st.selectbox("Available from", _TIME_OPTS,
                                    index=_TIME_OPTS.index(st.session_state.ws_label))
        with col_we:
            we_label = st.selectbox("Available until", _TIME_OPTS,
                                    index=_TIME_OPTS.index(st.session_state.we_label))

        if ws_label != st.session_state.ws_label or we_label != st.session_state.we_label:
            st.session_state.ws_label = ws_label
            st.session_state.we_label = we_label
            _save_owner_to_db(owner_name, st.session_state.pets, st.session_state.tasks, ws_label, we_label)

        window_start     = _parse_ampm(ws_label)
        window_end       = _parse_ampm(we_label)
        total_window_min = (window_end.hour * 60 + window_end.minute) - (window_start.hour * 60 + window_start.minute)

        if total_window_min > 0:
            h, m = divmod(total_window_min, 60)
            st.info(f"Window: {window_start.strftime('%I:%M %p')} – {window_end.strftime('%I:%M %p')}  ({h}h {m}m available)")
        else:
            st.error("End time must be after start time.")

        st.markdown(f"**Pets for {owner_name}:**")
        if st.session_state.pets:
            for pi, pet_entry in enumerate(st.session_state.pets):
                pc1, pc2 = st.columns([5, 1])
                with pc1:
                    icon = _species_icons.get(pet_entry["species"], "🐾")
                    st.write(f"{icon} **{pet_entry['name']}** — {pet_entry['species']}")
                with pc2:
                    if st.button("Remove", key=f"rem_pet_{pi}"):
                        removed = st.session_state.pets[pi]["name"]
                        st.session_state.pets.pop(pi)
                        st.session_state.tasks = [t for t in st.session_state.tasks if t.get("pet") != removed]
                        _save_owner_to_db(owner_name, st.session_state.pets, st.session_state.tasks,
                                          st.session_state.ws_label, st.session_state.we_label)
                        st.rerun()
        else:
            st.info("No pets yet. Add one below.")

        with st.form("add_pet_form", clear_on_submit=True):
            fp1, fp2, fp3 = st.columns([3, 2, 1])
            with fp1:
                new_pet_name = st.text_input("Pet name", placeholder="e.g. Mochi")
            with fp2:
                new_pet_species = st.selectbox("Species", ["dog", "cat", "other"])
            with fp3:
                st.markdown("<br>", unsafe_allow_html=True)
                add_pet_btn = st.form_submit_button("Add pet", use_container_width=True)

        if add_pet_btn:
            name_stripped = new_pet_name.strip()
            if not name_stripped:
                st.error("Pet name cannot be empty.")
            elif any(p["name"] == name_stripped for p in st.session_state.pets):
                st.warning(f"A pet named '{name_stripped}' already exists.")
            else:
                st.session_state.pets.append({"name": name_stripped, "species": new_pet_species})
                owner = get_owner(owner_name)
                find_or_create_pet(owner, name_stripped, new_pet_species)
                _save_owner_to_db(owner_name, st.session_state.pets, st.session_state.tasks,
                                  st.session_state.ws_label, st.session_state.we_label)
                st.success(f"Added {new_pet_species}: {name_stripped}")
                st.rerun()

        st.divider()
        bs1, bs2 = st.columns(2)
        with bs1:
            if st.button("Save now", use_container_width=True):
                _save_owner_to_db(owner_name, st.session_state.pets, st.session_state.tasks,
                                  st.session_state.ws_label, st.session_state.we_label)
                st.success(f"Saved profile for **{owner_name}**.")
        with bs2:
            if st.button("Reset profile", type="secondary", use_container_width=True):
                _delete_owner_from_db(owner_name)
                if os.path.exists("data.json"):
                    os.remove("data.json")
                st.session_state["owner"] = Owner(name="")
                st.session_state.tasks = []
                st.session_state.pets  = []
                st.session_state.active_owner_name = ""
                st.session_state.creating_new_owner = False
                st.session_state.ws_label = "8:00 AM"
                st.session_state.we_label = "12:00 PM"
                st.success("Profile cleared.")
                st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — Tasks
# ══════════════════════════════════════════════════════════════════════════════
with tab2:
    st.caption(
        "Add each care task. For strict tasks (e.g. medicine at exactly 9:00 AM) "
        "enable **Fixed start time** — otherwise the app picks the best slot automatically."
    )

    pet_names = [p["name"] for p in st.session_state.pets]

    col1, col2, col3 = st.columns([3, 1, 1])
    with col1:
        task_title = st.text_input("Task name", value="Walk dog")
    with col2:
        duration = st.number_input("Duration (min)", min_value=1, max_value=240, value=30)
    with col3:
        priority = st.selectbox("Priority", ["low", "medium", "high"], index=1)

    col4, col5, col6 = st.columns([2, 2, 2])
    with col4:
        preferred_time = st.selectbox(
            "Preferred time of day", ["morning", "afternoon", "evening", "anytime"],
            index=0, help="The app tries to place the task in this part of the day.",
        )
    with col5:
        use_fixed = st.checkbox("Fixed start time (must happen at exact time)")
        fixed_start = None
        if use_fixed:
            fixed_t = st.time_input("Fixed start time", value=time(9, 0))
            fixed_start = f"{fixed_t.hour:02d}:{fixed_t.minute:02d}"
    with col6:
        if pet_names:
            task_pet = st.selectbox("Which pet?", pet_names)
        else:
            st.caption("Add a pet in the Owner & Pets tab first.")
            task_pet = None

    if st.button("Add task", type="primary"):
        if not owner_name:
            st.error("Select or create an owner in the Owner & Pets tab first.")
        elif not task_title.strip():
            st.error("Task name cannot be empty.")
        elif not pet_names:
            st.error("Add at least one pet first.")
        else:
            owner = get_owner(owner_name)
            pet_species = next((p["species"] for p in st.session_state.pets if p["name"] == task_pet), "other")
            pet = find_or_create_pet(owner, task_pet, pet_species)
            pri_map = {"low": 1, "medium": 2, "high": 3}
            next_id = max((t.id or 0 for t in owner.get_all_tasks()), default=0) + 1
            task_obj = Task(
                id=next_id, pet_id=pet.id, title=task_title.strip(),
                duration_minutes=int(duration), priority=pri_map.get(priority, 2),
                priority_level=priority,
            )
            pet.add_task(task_obj)
            st.session_state.tasks.append({
                "title": task_title.strip(), "duration_minutes": int(duration),
                "priority": priority,
                "preferred_time": preferred_time if preferred_time != "anytime" else None,
                "fixed_start_time": fixed_start, "pet": task_pet,
            })
            _save_owner_to_db(owner_name, st.session_state.pets, st.session_state.tasks,
                              st.session_state.ws_label, st.session_state.we_label)
            label = f"fixed at {fixed_start}" if fixed_start else preferred_time
            st.success(f"Added: {task_title} ({task_pet}) — {priority} priority, {duration} min, {label}")

    # Task list
    if st.session_state.tasks:
        st.write("**Your tasks:** *(edit duration, priority, preferred time, or fixed time directly in the row)*")
        hdr = st.columns([2, 1, 1, 2, 2, 2, 1])
        for col, label in zip(hdr, ["Task", "Pet", "Min", "Priority", "Preferred time", "Fixed at (HH:MM)", ""]):
            col.markdown(f"<small><b>{label}</b></small>", unsafe_allow_html=True)

        for i, task in enumerate(st.session_state.tasks):
            ca, cb, cc, cd, ce, cf, cg = st.columns([2, 1, 1, 2, 2, 2, 1])
            with ca:
                st.write(task["title"])
            with cb:
                st.write(task.get("pet") or "—")
            with cc:
                new_dur = st.number_input("Min", min_value=1, max_value=240,
                                          value=task["duration_minutes"], key=f"dur_{i}",
                                          label_visibility="collapsed")
                st.session_state.tasks[i]["duration_minutes"] = int(new_dur)
            with cd:
                new_prio = st.selectbox("Priority", ["low", "medium", "high"],
                                        index=["low", "medium", "high"].index(task.get("priority", "medium")),
                                        key=f"prio_{i}", label_visibility="collapsed")
                st.session_state.tasks[i]["priority"] = new_prio
            with ce:
                pt_opts = ["morning", "afternoon", "evening", "anytime"]
                curr_pt = task.get("preferred_time") or "anytime"
                new_pt = st.selectbox("Preferred", pt_opts, index=pt_opts.index(curr_pt),
                                      key=f"pt_{i}", label_visibility="collapsed")
                st.session_state.tasks[i]["preferred_time"] = new_pt if new_pt != "anytime" else None
            with cf:
                curr_fixed = task.get("fixed_start_time") or ""
                new_fixed = st.text_input("Fixed", value=curr_fixed, key=f"fxt_{i}",
                                          placeholder="e.g. 09:00", label_visibility="collapsed")
                new_fixed = new_fixed.strip()
                if new_fixed:
                    if _re.match(r"^\d{1,2}:\d{2}$", new_fixed):
                        st.session_state.tasks[i]["fixed_start_time"] = new_fixed
                    else:
                        st.caption("⚠️ use HH:MM")
                else:
                    st.session_state.tasks[i]["fixed_start_time"] = None
            with cg:
                if st.button("✕", key=f"del_{i}"):
                    owner = get_owner(owner_name) if owner_name else Owner(name="")
                    for p in owner.pets:
                        p.tasks = [t for t in p.tasks if not (
                            t.title == task["title"] and t.duration_minutes == task["duration_minutes"]
                        )]
                    st.session_state.tasks.pop(i)
                    if owner_name:
                        _save_owner_to_db(owner_name, st.session_state.pets, st.session_state.tasks,
                                          st.session_state.ws_label, st.session_state.we_label)
                    st.rerun()
    else:
        st.info("No tasks yet. Add one above.")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — Generate Schedule
# ══════════════════════════════════════════════════════════════════════════════
with tab3:
    if st.button("Generate schedule", type="primary"):
        tasks = st.session_state.tasks
        if not tasks:
            st.warning("Add at least one task in the Tasks tab first.")
        elif not owner_name:
            st.warning("Select an owner in the Owner & Pets tab first.")
        elif total_window_min <= 0:
            st.error("Fix the available window in the Owner & Pets tab.")
        else:
            scheduled, unscheduled = build_daily_schedule(window_start, window_end, tasks)

            valid = validate_tasks(tasks)
            with st.expander("Step 1 — Validate tasks", expanded=True):
                st.write(f"**{len(valid)}** valid task(s) out of {len(tasks)} submitted.")
                bad = len(tasks) - len(valid)
                if bad:
                    st.warning(f"{bad} task(s) skipped (empty name or zero duration).")

            flexible = [t for t in valid if not t.get("fixed_start_time")]
            ranked   = rank_tasks(flexible)
            with st.expander("Step 2 — Rank flexible tasks by score", expanded=True):
                rank_rows = [
                    {"Rank": i + 1, "Task": t["title"], "Pet": t.get("pet") or "—",
                     "Priority": t.get("priority", "medium"),
                     "Preferred time": t.get("preferred_time") or "any", "Score": t["_score"]}
                    for i, t in enumerate(ranked)
                ]
                fixed_count = len([t for t in valid if t.get("fixed_start_time")])
                if fixed_count:
                    st.info(f"{fixed_count} task(s) are fixed-time and skipped scoring.")
                if rank_rows:
                    st.dataframe(rank_rows, use_container_width=True, hide_index=True)

            with st.expander("Step 3 — Place tasks into time slots", expanded=True):
                total_used = sum(t["duration_minutes"] for t in scheduled)
                st.write(f"**{len(scheduled)}** task(s) placed using **{total_used} min** of **{total_window_min} min** available.")
                if unscheduled:
                    st.warning(f"{len(unscheduled)} task(s) could not be placed: " +
                               ", ".join(t["title"] for t in unscheduled))

            with st.expander("Step 4 — Explain decisions", expanded=True):
                for entry in scheduled:
                    icon = "📌" if entry["fixed"] else "✅"
                    pet_label = f" [{entry.get('pet', '')}]" if entry.get("pet") else ""
                    st.markdown(f"{icon}{pet_label} {entry['explanation']}")
                for t in unscheduled:
                    st.markdown(f"❌ **{t['title']}** — {t['reason']}")

            st.divider()
            st.markdown("### Your Daily Schedule")
            if scheduled:
                color_map = {"high": "#ffd6d6", "medium": "#fff4cc", "low": "#ddffdd"}
                pin_color = "#e8f0ff"
                html = ["<table style='border-collapse:collapse;width:100%'>", "<tr>",
                        *[f"<th style='text-align:left;padding:10px 8px;border-bottom:2px solid #ccc;"
                          f"background:#f5f5f5'>{h}</th>"
                          for h in ["Time", "Pet", "Task", "Duration", "Priority", "Explanation"]],
                        "</tr>"]
                for entry in scheduled:
                    p   = entry["priority"]
                    bg  = pin_color if entry["fixed"] else color_map.get(p, "#fff4cc")
                    ico = _em.get(p, "🟡")
                    pin = "📌 " if entry["fixed"] else ""
                    pne = entry.get("pet") or ""
                    pse = next((pe["species"] for pe in st.session_state.pets if pe["name"] == pne), "other")
                    pet_cell = f"{_species_icons.get(pse,'🐾')} {pne}" if pne else "—"
                    html.append(
                        f"<tr style='background:{bg}'>"
                        f"<td style='padding:10px 8px;border-bottom:1px solid #eee;font-weight:bold;white-space:nowrap'>{entry['start_fmt']} – {entry['end_fmt']}</td>"
                        f"<td style='padding:10px 8px;border-bottom:1px solid #eee;white-space:nowrap'>{pet_cell}</td>"
                        f"<td style='padding:10px 8px;border-bottom:1px solid #eee'>{pin}{ico} {entry['title']}</td>"
                        f"<td style='padding:10px 8px;border-bottom:1px solid #eee'>{entry['duration_minutes']} min</td>"
                        f"<td style='padding:10px 8px;border-bottom:1px solid #eee'>{p.title()}</td>"
                        f"<td style='padding:10px 8px;border-bottom:1px solid #eee;font-style:italic;color:#555'>{entry['explanation']}</td>"
                        "</tr>"
                    )
                html.append("</table>")
                st.markdown(
                    "<div style='overflow-x:auto'>" + "".join(html) + "</div>",
                    unsafe_allow_html=True,
                )

                if st.session_state.pets and len(st.session_state.pets) > 1:
                    st.markdown("#### Per-pet summary")
                    pet_tasks: dict = defaultdict(list)
                    for entry in scheduled:
                        pet_tasks[entry.get("pet") or "Unknown"].append(entry)
                    scols = st.columns(len(st.session_state.pets))
                    for col, pe in zip(scols, st.session_state.pets):
                        pn = pe["name"]; ps = pe["species"]
                        entries = pet_tasks.get(pn, [])
                        col.metric(f"{_species_icons.get(ps,'🐾')} {pn}",
                                   f"{len(entries)} task(s)", f"{sum(e['duration_minutes'] for e in entries)} min")

                if unscheduled:
                    st.markdown("**Not scheduled:**")
                    for t in unscheduled:
                        st.markdown(f"- ❌ **{t['title']}**: {t['reason']}")
            else:
                st.info("No tasks could be placed in the selected window.")

            flat = [{"title": e["title"], "duration_minutes": e["duration_minutes"],
                     "priority": e["priority"]} for e in scheduled]
            metrics = evaluate_plan(tasks, flat, total_window_min)
            st.divider()
            st.markdown("### AI Performance Metrics")
            m1, m2, m3, m4 = st.columns(4)
            def _pct(v): return f"{v * 100:.1f}%"
            m1.metric("Task Coverage",       _pct(metrics["task_coverage"]),       help="% of valid tasks scheduled")
            m2.metric("Time Efficiency",     _pct(metrics["time_efficiency"]),     help="% of available window used")
            m3.metric("Priority Compliance", _pct(metrics["priority_compliance"]), help="No higher-priority task dropped while lower kept")
            m4.metric("Overall Score",       _pct(metrics["overall_score"]),       help="Average of the three metrics")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 — AI Reliability
# ══════════════════════════════════════════════════════════════════════════════
with tab4:
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
