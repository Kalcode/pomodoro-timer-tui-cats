"""Every tunable game number lives here (spec §3–§4). Later milestones add to this file."""

from pomo.game.events import RuleKind

PAUSE_ALLOWANCE_S = 3 * 60  # total pause per focus before it counts as a rule break

PENALTIES = {  # mood lost by every cat (spec §3.2)
    RuleKind.ABANDON_FOCUS: 25,
    RuleKind.SKIP_BREAK: 20,
    RuleKind.LONG_PAUSE: 10,
}
