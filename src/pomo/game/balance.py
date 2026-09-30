"""Every tunable game number lives here (spec §3–§4). Later milestones add to this file."""

from pomo.game.events import RuleKind

PAUSE_ALLOWANCE_S = 3 * 60  # total pause per focus before it counts as a rule break

PENALTIES = {  # mood lost by every cat (spec §3.2)
    RuleKind.ABANDON_FOCUS: 25,
    RuleKind.SKIP_BREAK: 20,
    RuleKind.LONG_PAUSE: 10,
}

# --- mood (spec §3.3) -------------------------------------------------------
MOOD_START = 80
MOOD_MAX = 100
CONTENT_AT = 70  # stage lower bounds: content ≥ 70 > grumpy ≥ 40 > pissy ≥ 15 > furious
GRUMPY_AT = 40
PISSY_AT = 15
FOCUS_REWARD = 10
FOCUS_REWARD_MIN_MINUTES = 15
BREAK_REWARD = 5
COOL_PER_S = 1 / 600  # anger cools by 1 per 10 minutes of runtime...
COOL_CEILING = 70  # ...but never past content on its own

# --- needs (spec §3.4) ------------------------------------------------------
NEED_FULL_S = {"hunger": 3 * 3600, "play": 2 * 3600, "affection": 2.5 * 3600}  # 0 → 100
NEED_ALERT = 70  # above this the cat wants something, shows a bubble, and gets sulky
NEED_DRAIN_PER_S = 1 / 60  # mood lost while a need is above the alert level...
NEED_FLOOR = 40  # ...which on its own never goes past grumpy
EAT_MOOD = 3  # kibble; pissy and furious cats eat but don't cheer up

# --- traits (spec §3.5) -----------------------------------------------------
TRAIT_PENALTY = {"chill": 0.5, "diva": 1.5}
CLINGY_AFFECTION = 1.5
