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

# --- behaviour (spec §3.1, §3.7, §6) ----------------------------------------
WALK_SPEED = 10.0  # columns per second
ZOOM_SPEED = 30.0
JUMP_BASE_S = 0.35
JUMP_PER_PX_S = 0.012
JUMP_ARC_PX = 4  # a jump rises this much plus half the height difference above the straight line
SIT_S = (8.0, 25.0)  # (min, max) seconds
LOAF_S = (15.0, 45.0)
NAP_S = (90.0, 300.0)
SULK_S = (20.0, 60.0)
EAT_S = 6.0
BEG_S = 10.0
AWAY_S = (20.0, 40.0)  # a trip through the litter door
LITTER_EVERY_S = (20 * 60.0, 40 * 60.0)
ZOOM_LEGS = (3, 5)
NAP_SPOTS = {"tree_top": 3, "tree_mid": 2, "shelf": 2, "floor": 1}  # cats like to nap up high
ACTIVITY_WEIGHTS = {  # per mode: focus is nap time, a break is play time (spec §3.1)
    "nap": {"nap": 60, "loaf": 20, "sit": 10, "wander": 8, "climb": 2},
    "play": {"zoom": 25, "wander": 25, "climb": 20, "sit": 15, "loaf": 10, "nap": 5},
    "relax": {"wander": 25, "climb": 15, "sit": 25, "loaf": 20, "nap": 15},
}
