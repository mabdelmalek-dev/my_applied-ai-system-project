# PawPal+ Project Extended

## Reflection and Ethics: Responsible AI 

### Limitations and biases in the system

The scheduling logic has several built-in assumptions that may not fit every user:

- **Hardcoded priority weights.** The scores high=100, medium=50, low=10 are arbitrary constants, not learned from data. A task labeled "medium" by one owner might be far more urgent than a "high" task for another. The system has no way to distinguish that nuance.
- **Rigid time zones.** "Morning" is always defined as before 12:00 PM, "afternoon" as 12–5 PM, and "evening" as after 5 PM. These zones don't adapt to the owner's actual routine — a night-shift worker's "morning" is entirely different.
- **No rest time between tasks.** The scheduler places tasks back-to-back with no buffer. A real pet care plan often needs transition time between activities. The current model could inadvertently create an over-packed, unrealistic schedule.
- **No task dependencies.** The system doesn't know that "give medication" might need to happen *after* "feed breakfast." Tasks are treated as fully independent, which can produce technically valid but practically awkward orderings.
- **Confidence scores are rule-based, not learned.** The 0–100% confidence rating is computed from a fixed formula (priority + time-zone match). It doesn't reflect actual historical accuracy or adapt as the owner uses the app over time.

### Could this app be misused? How would I prevent it?

- **Over-scheduling pets.** A user could fill every minute of a 12-hour window with tasks, and the system would schedule them all without flagging that a pet needs rest. A responsible improvement would be adding a maximum daily activity limit per pet and enforcing minimum gaps between physically demanding tasks.
- **Medication mismanagement.** If a medically critical fixed task is rejected (e.g., moved to "unscheduled"), the app doesn't escalate or alert. A future version should show a prominent warning for any rejected high-priority fixed task.
- **False confidence from metrics.** Showing "Priority Compliance: 100%" and "Overall Score: 97%" could lead a user to trust the schedule uncritically. These numbers measure internal consistency — not whether the plan is actually good for the pet's wellbeing. The app should make that distinction clearer.

The most effective safeguard already in place is transparency: every rejection comes with a plain-English reason, and confidence scores below 70% are shown in orange or red to signal uncertainty.

### What surprised me while testing the AI's reliability

The biggest surprise was how robust priority compliance turned out to be — 100% across all 6 benchmark scenarios and 55 unit tests. I expected the greedy scheduler to occasionally slip, but the architecture makes it structurally impossible: the ranker sorts tasks by score *before* the scheduler sees them, so the greedy loop always encounters high-priority tasks first.

The second surprise was how much the confidence score revealed. When I added the confidence column to the schedule table, I could immediately spot tasks placed far outside their preferred time zone — technically "scheduled" but with low scores. Without confidence scoring, those cases looked like successes. With it, I could see the AI was doing something suboptimal that pass/fail metrics alone were hiding.

### My collaboration with AI during this project

I used Claude (via Claude Code) as a coding assistant throughout — from the initial class scaffolding in Module 1 through to the final UI, tests, and documentation.

**One instance where the AI's suggestion was genuinely helpful:**
When the schedule HTML table caused the entire page to scroll horizontally, the AI immediately identified the root cause and suggested wrapping the table in `<div style='overflow-x:auto'>`. This was exactly right — it contained the scroll to the table itself without affecting the rest of the page — and it was a fix I wouldn't have reached as quickly on my own.

**One instance where the AI's suggestion was flawed:**
When I asked to make the app content area wider, the AI first switched from `layout="centered"` to `layout="wide"`, which made the content stretch across the full screen — the opposite of what I wanted. It then suggested CSS `max-width` overrides that had no visible effect because Streamlit's centered layout enforces its own width constraint that ordinary CSS cannot override without `!important`. It took several back-and-forth rounds before we landed on the correct fix. The AI was confident in each intermediate suggestion even when it wasn't working — a good reminder that AI assistants can be wrong and that testing the running app is always the final authority.
