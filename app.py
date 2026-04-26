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

st.markdown("""
<div style="width:100%;border-radius:999px;background:linear-gradient(135deg,#fff8f0 0%,#fde8c8 45%,#f5c07a 100%);border:1.5px solid #e8c49a;box-shadow:0 4px 18px rgba(160,82,45,0.13);margin-bottom:14px;">
  <div style="display:flex;align-items:center;justify-content:space-between;padding:18px 28px;">
    <div style="display:flex;align-items:flex-end;gap:4px;">
      <span style="font-size:3.2rem;">🐕</span>
      <span style="font-size:1.8rem;opacity:0.5;margin-bottom:4px;">🐾</span>
      <span style="font-size:2.6rem;">🐈</span>
    </div>
    <div style="text-align:center;flex:1;padding:0 16px;">
      <div style="font-size:2rem;font-weight:900;color:#7B3F1A;letter-spacing:2px;">🐾 PawPal+</div>
      <div style="font-size:0.75rem;color:#A0522D;margin-top:4px;letter-spacing:1.5px;font-weight:600;text-transform:uppercase;">AI · Pet Care · Daily Planner</div>
      <div style="margin-top:10px;display:flex;justify-content:center;gap:8px;">
        <span style="background:#A0522D;color:#fff;border-radius:20px;padding:3px 12px;font-size:0.68rem;font-weight:700;letter-spacing:1px;">SMART</span>
        <span style="background:#D2691E;color:#fff;border-radius:20px;padding:3px 12px;font-size:0.68rem;font-weight:700;letter-spacing:1px;">EXPLAINABLE</span>
        <span style="background:#8B4513;color:#fff;border-radius:20px;padding:3px 12px;font-size:0.68rem;font-weight:700;letter-spacing:1px;">RELIABLE</span>
      </div>
    </div>
    <div style="display:flex;align-items:flex-end;gap:4px;">
      <span style="font-size:2.6rem;">🦮</span>
      <span style="font-size:1.8rem;opacity:0.5;margin-bottom:4px;">🐾</span>
      <span style="font-size:3.2rem;">🐩</span>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)


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

# ── Theme styling (tabs + buttons) ───────────────────────────────────────────
st.markdown("""
<style>
/* Tab strip */
.stTabs [data-baseweb="tab-list"] {
    gap: 6px;
    border-bottom: 3px solid #A0522D;
    padding-bottom: 0;
}
/* Every tab button — all same warm cream base */
.stTabs [data-baseweb="tab"] {
    background: #fdf3e7;
    border: 2px solid #A0522D;
    border-bottom: none;
    border-radius: 8px 8px 0 0;
    color: #7B3F1A;
    font-weight: 600;
    font-size: 0.92rem;
    padding: 8px 18px;
    transition: background 0.15s, color 0.15s;
}
/* Active tab — same background, just a bold bottom accent */
.stTabs [aria-selected="true"] {
    background: #fdf3e7 !important;
    color: #7B3F1A !important;
    border-color: #A0522D !important;
    border-bottom: 3px solid #A0522D !important;
    font-weight: 800 !important;
}
/* Hover */
.stTabs [data-baseweb="tab"]:hover {
    background: #f5e0c8 !important;
    color: #7B3F1A !important;
    border-color: #8B4513 !important;
}
/* Hide the default underline indicator */
.stTabs [data-baseweb="tab-highlight"] { background: transparent !important; }
.stTabs [data-baseweb="tab-border"]    { display: none !important; }

/* ── Buttons — warm golden-brown to match pet emoji palette ── */
/* All buttons base (secondary style) */
.stButton > button,
.stFormSubmitButton > button {
    background-color: #fdf3e7 !important;
    border: 1px solid #A0522D !important;
    color: #7B3F1A !important;
    border-radius: 8px !important;
    font-weight: 500 !important;
}
.stButton > button:hover,
.stFormSubmitButton > button:hover {
    background-color: #f5e0c8 !important;
    border-color: #8B4513 !important;
    color: #7B3F1A !important;
}

/* Primary buttons — must come AFTER the general rule to win */
.stButton > button[kind="primary"],
.stFormSubmitButton > button[kind="primary"],
button[data-testid="baseButton-primary"] {
    background-color: #A0522D !important;
    border-color: #A0522D !important;
    color: #ffffff !important;
    font-weight: 600 !important;
}
.stButton > button[kind="primary"]:hover,
.stFormSubmitButton > button[kind="primary"]:hover,
button[data-testid="baseButton-primary"]:hover {
    background-color: #8B4513 !important;
    border-color: #8B4513 !important;
    color: #ffffff !important;
}
</style>
""", unsafe_allow_html=True)

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab1, tab2, tab3 = st.tabs([
    "🐾  Owner & Pets",
    "📋  Tasks",
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
            st.session_state.active_owner_name = ""
            st.session_state.pets = []
            st.session_state.tasks = []
            st.session_state.ws_label = "8:00 AM"
            st.session_state.we_label = "12:00 PM"
            st.session_state["owner"] = Owner(name="")
            st.rerun()

    # Clear data when placeholder is re-selected after a profile was loaded
    if owner_choice == _PLACEHOLDER and st.session_state.active_owner_name:
        st.session_state.active_owner_name = ""
        st.session_state.pets = []
        st.session_state.tasks = []
        st.session_state.ws_label = "8:00 AM"
        st.session_state.we_label = "12:00 PM"
        st.session_state["owner"] = Owner(name="")
        st.session_state.creating_new_owner = False
        st.rerun()

    # Auto-load on dropdown change to a different existing owner
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

    # ── Generate Schedule button (bottom of Tasks tab) ────────────────────────
    st.divider()

# ── Confidence scoring helper ─────────────────────────────────────────────────
def _confidence_score(entry: dict) -> int:
    """Rate how confident the AI is in this scheduling decision (0-100)."""
    if entry.get("fixed"):
        return 100  # owner locked the time — no ambiguity
    priority  = entry.get("priority", "medium")
    preferred = entry.get("preferred_time")
    hour      = entry["start_time"].hour
    score = {"high": 85, "medium": 70, "low": 55}.get(priority, 70)
    if preferred:
        zone_ok = (
            (preferred == "morning"   and hour < 12) or
            (preferred == "afternoon" and 12 <= hour < 17) or
            (preferred == "evening"   and hour >= 17)
        )
        score += 10 if zone_ok else -10
    return max(0, min(100, score))


def _conf_bar(pct: int) -> str:
    filled = round(pct / 10)
    bar    = "█" * filled + "░" * (10 - filled)
    color  = "#27ae60" if pct >= 80 else "#e67e22" if pct >= 60 else "#e74c3c"
    return f"<span style='font-family:monospace;color:{color}'>{bar}</span> {pct}%"


with tab2:
    if st.button("📅 Generate My Schedule", type="primary"):
        tasks = st.session_state.tasks
        if not tasks:
            st.warning("Add at least one task above first.")
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
                    tip = entry.get("care_tip")
                    if tip:
                        st.caption(f"💡 *Retrieved care tip:* {tip}")
                for t in unscheduled:
                    st.markdown(f"❌ **{t['title']}** — {t['reason']}")

            st.divider()
            st.markdown("### Your Daily Schedule")
            if scheduled:
                for entry in scheduled:
                    entry["_conf"] = _confidence_score(entry)
                avg_conf = round(sum(e["_conf"] for e in scheduled) / len(scheduled))

                color_map = {"high": "#ffd6d6", "medium": "#fff4cc", "low": "#ddffdd"}
                pin_color = "#e8f0ff"
                html = ["<table style='border-collapse:collapse;width:100%'>", "<tr>",
                        *[f"<th style='text-align:left;padding:10px 8px;border-bottom:2px solid #ccc;"
                          f"background:#f5f5f5'>{h}</th>"
                          for h in ["Time", "Pet", "Task", "Duration", "Priority", "Confidence", "Explanation"]],
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
                        f"<td style='padding:10px 8px;border-bottom:1px solid #eee;white-space:nowrap'>{_conf_bar(entry['_conf'])}</td>"
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

                with st.expander("📋 Decision log", expanded=False):
                    st.caption("Full record of every accept/reject decision the AI made.")
                    for entry in scheduled:
                        conf = entry["_conf"]
                        st.markdown(f"✅ **{entry['title']}** — scheduled at {entry['start_fmt']} "
                                    f"| priority: {entry['priority']} | confidence: {conf}%")
                        tip = entry.get("care_tip")
                        if tip:
                            st.caption(f"💡 *Care tip:* {tip}")
                    for t in unscheduled:
                        st.markdown(f"❌ **{t['title']}** — rejected | reason: _{t['reason']}_")
            else:
                st.info("No tasks could be placed in the selected window.")

            flat = [{"title": e["title"], "duration_minutes": e["duration_minutes"],
                     "priority": e["priority"]} for e in scheduled]
            metrics = evaluate_plan(tasks, flat, total_window_min)
            st.divider()
            st.markdown("### AI Performance Metrics")
            m1, m2, m3, m4, m5 = st.columns(5)
            def _pct(v): return f"{v * 100:.1f}%"
            m1.metric("Task Coverage",       _pct(metrics["task_coverage"]),       help="% of valid tasks scheduled")
            m2.metric("Time Efficiency",     _pct(metrics["time_efficiency"]),     help="% of available window used")
            m3.metric("Priority Compliance", _pct(metrics["priority_compliance"]), help="No higher-priority task dropped while lower kept")
            m4.metric("Overall Score",       _pct(metrics["overall_score"]),       help="Average of the three metrics")
            if scheduled:
                m5.metric("Avg Confidence",  f"{avg_conf}%", help="Average AI confidence across scheduled tasks")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — AI Reliability
# ══════════════════════════════════════════════════════════════════════════════
with tab3:
    import subprocess, sys

    # ── Unit test runner ──────────────────────────────────────────────────────
    st.markdown("#### Automated Unit Tests")
    st.caption("Runs the full pytest suite (55 tests across 5 files) live in the background.")
    if st.button("▶ Run unit tests now"):
        with st.spinner("Running pytest…"):
            proc = subprocess.run(
                [sys.executable, "-m", "pytest", "tests/", "-v", "--tb=short", "--no-header"],
                capture_output=True, text=True,
            )
        output = proc.stdout + proc.stderr
        passed = output.count(" PASSED")
        failed = output.count(" FAILED")
        error  = output.count(" ERROR")
        if proc.returncode == 0:
            st.success(f"All {passed} unit tests passed.")
        else:
            st.error(f"{failed} test(s) failed, {error} error(s). {passed} passed.")
        with st.expander("Full pytest output", expanded=proc.returncode != 0):
            st.code(output, language="text")

    st.divider()

    # ── Benchmark scenarios ───────────────────────────────────────────────────
    st.markdown("#### Benchmark Scenarios")

    # Auto-run benchmarks and show summary
    _results = run_benchmarks()
    _n_total = len(_results)
    _n_pass  = sum(1 for r in _results if r["passed"])
    _n_fail  = _n_total - _n_pass
    _avg_overall = sum(r["metrics"]["overall_score"] for r in _results) / _n_total
    _avg_compliance = sum(r["metrics"]["priority_compliance"] for r in _results) / _n_total
    _avg_coverage   = sum(r["metrics"]["task_coverage"] for r in _results) / _n_total

    if _n_fail == 0:
        _struggle = "The AI handled all scenarios correctly, including edge cases like empty task lists and overlapping fixed times."
    else:
        _failed_names = [r["name"] for r in _results if not r["passed"]]
        _struggle = f"The AI struggled with: {'; '.join(_failed_names)}."

    if _avg_compliance == 1.0:
        _compliance_note = "Priority compliance was perfect (100%) — high-priority tasks were always scheduled before lower-priority ones."
    else:
        _compliance_note = f"Priority compliance averaged {_avg_compliance*100:.0f}% — some lower-priority tasks were occasionally scheduled over higher ones."

    st.markdown(
        f"""
        <div style="background:#fff8f0;border-left:4px solid #c0392b;border-radius:6px;padding:16px 20px;margin-bottom:16px">
        <b>Testing Summary</b><br><br>
        {_n_pass} out of {_n_total} benchmark tests passed.
        {_struggle}<br><br>
        Overall scores averaged <b>{_avg_overall*100:.0f}%</b> and task coverage averaged <b>{_avg_coverage*100:.0f}%</b> across all scenarios.
        {_compliance_note}
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.caption("Expand each scenario below to inspect individual results.")
    if st.button("Re-run benchmark tests"):
        _results = run_benchmarks()
        _n_pass  = sum(1 for r in _results if r["passed"])
        _n_fail  = len(_results) - _n_pass
    if _n_fail == 0:
        st.success(f"All {_n_pass} benchmarks passed!")
    else:
        st.error(f"{_n_fail} benchmark(s) failed, {_n_pass} passed.")
    for r in _results:
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
