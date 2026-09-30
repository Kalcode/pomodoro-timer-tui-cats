import random

import pytest

from pomo.game.behavior import Doing, Mode
from pomo.game.cat import Cat, Trait
from pomo.game.events import Played
from pomo.game.tools import Tool
from pomo.game.toys import Ball, String
from pomo.game.world import World

TICK = 0.125
FLOOR = 57  # in a 70×58 room


def room(*names: str, seed: int = 1, width: int = 70) -> World:
    world = World([Cat(name, "tabby", Trait.CLINGY) for name in names], random.Random(seed), width, 58)
    world.set_mode(Mode.PLAY)
    return world


def run(world: World, seconds: float, each=None) -> None:
    for _ in range(int(seconds / TICK)):
        world.tick(TICK)
        if each:
            each(world)


def playful(world: World) -> Cat:
    """Mango, content and keen to play."""
    mango = world.cats[0]
    mango.needs["play"] = 90
    return mango


class AlwaysHigh(random.Random):
    """Every roll comes out 0.99: a cat goes for a toy only if it's certain to."""

    def random(self) -> float:
        return 0.99


# --- the ball on its own ----------------------------------------------------------

def test_a_dropped_ball_bounces_lower_each_time_then_rests():
    ball = Ball(30, 10)
    peaks, rising = [], False
    for _ in range(5 * 32):
        before = ball.y
        ball.tick(1 / 32, 70, FLOOR)
        if ball.y < before:
            rising = True
        elif rising:
            peaks.append(before)
            rising = False
    assert len(peaks) >= 2
    assert all(later > earlier for earlier, later in zip(peaks, peaks[1:]))  # lower bounces: bigger y
    assert (ball.y, ball.vy) == (FLOOR, 0)


def test_a_rolling_ball_slows_to_a_stop():
    ball = Ball(10, FLOOR, vx=20)
    ball.tick(2.0, 70, FLOOR)
    assert ball.vx == 0
    assert ball.x == pytest.approx(20, abs=0.5)  # v² / 2a = 400 / 40


def test_the_ball_bounces_off_the_walls():
    ball = Ball(60, FLOOR, vx=40)
    ball.tick(0.5, 70, FLOOR)
    assert ball.vx < 0
    assert ball.x <= 67.5


def test_a_long_tick_cannot_throw_the_ball_out_of_the_room():
    ball = Ball(35, 10, vx=300)
    ball.tick(1.0, 70, FLOOR)
    assert 2.5 <= ball.x <= 67.5
    assert ball.y <= FLOOR


def test_the_string_tip_swings_past_the_mouse_and_settles_under_it():
    string = String(20, 20, 30)
    string.anchor = 30
    furthest = 0.0
    for _ in range(3 * 32):
        string.tick(1 / 32)
        furthest = max(furthest, string.tip_x)
    assert furthest > 31  # it swung past
    assert string.tip_x == pytest.approx(30, abs=0.5)


def test_a_long_tick_cannot_make_the_string_fly_off():
    string = String(20, 20, 30)
    string.anchor = 40
    string.tick(1.0)
    assert 20 <= string.tip_x <= 60


# --- the ball in the room -----------------------------------------------------------

def test_clicking_with_the_ball_drops_it_at_the_pointer():
    world = room("Mango")
    world.hold(Tool.BALL)
    world.click(30, 20)
    ball = world.view().ball
    assert (ball.x, ball.y) == (30, 20)
    run(world, 3)
    assert world.view().ball.y == FLOOR


def test_there_is_only_ever_one_ball():
    world = room("Mango")
    world.hold(Tool.BALL)
    world.click(30, 20)
    world.click(50, 40)
    assert (world.ball.x, world.ball.y) == (50, 40)


def test_the_yarn_turns_as_it_rolls():
    world = room("Mango")
    world.hold(Tool.BALL)
    world.click(30, FLOOR)
    frames = set()
    run(world, 1, lambda w: frames.add(w.view().ball.frame))
    assert frames == {0, 1}


def test_a_playful_cat_chases_bats_and_finishes_a_session():
    world = room("Mango")
    mango = playful(world)
    world.hold(Tool.BALL)
    world.click(60, 30)
    fastest, poses = 0.0, set()

    def watch(w):
        nonlocal fastest
        fastest = max(fastest, abs(w.ball.vx))
        poses.update(c.pose for c in w.view().cats)

    run(world, 12, watch)
    assert fastest >= 25  # batted: a dropped ball never rolls faster than 20
    assert "leap" in poses  # pounced
    assert Played("Mango", "ball") in world.take_news()
    assert mango.needs["play"] == pytest.approx(40, abs=1)
    assert mango.mood > 84


def test_a_cat_with_no_need_to_play_can_ignore_the_ball():
    world = room("Mango")
    world.rng = AlwaysHigh()
    world.hold(Tool.BALL)
    world.click(60, 30)
    run(world, 20)
    assert world.playing == {}
    assert world.take_news() == []


@pytest.mark.parametrize("mood", [30, 10])
def test_angry_cats_refuse_toys(mood):
    world = room("Mango")
    mango = playful(world)
    mango.mood = mood
    world.hold(Tool.BALL)
    world.click(60, 30)
    run(world, 20)
    assert world.playing == {}
    assert mango.needs["play"] > 90


def test_a_hungry_cat_eats_before_it_plays():
    world = room("Mango")
    mango = playful(world)
    mango.needs["hunger"] = 90
    world.hold(Tool.BALL)
    world.click(20, 30)
    assert world.playing == {}
    run(world, 20)
    assert mango.needs["hunger"] < 5


def test_a_focus_starting_ends_play_and_leaves_the_ball_where_it_is():
    world = room("Mango")
    mango = playful(world)
    world.hold(Tool.BALL)
    world.click(60, 30)
    run(world, 2)
    assert "Mango" in world.playing
    world.set_mode(Mode.NAP)
    assert (world.playing, world.tool) == ({}, None)
    run(world, 30)
    assert world.ball is not None
    assert world.take_news() == []
    assert mango.needs["play"] > 85


def test_petting_a_playing_cat_stops_the_game():
    world = room("Mango")
    playful(world)
    world.cats[0].needs["affection"] = 60
    world.hold(Tool.BALL)
    world.click(60, 30)
    run(world, 1)
    x = world.bodies["Mango"].x
    world.hold(Tool.PET)
    for i in range(7):
        world.point(x - 3 + i, FLOOR - 6)
    assert world.playing == {}
    assert world.bodies["Mango"].step.doing is Doing.PURR


# --- the string ---------------------------------------------------------------------

def test_the_string_hangs_where_the_pointer_is_and_goes_with_it():
    world = room("Mango")
    world.hold(Tool.STRING)
    assert world.view().string is None
    world.point(20, 30)
    string = world.view().string
    assert (string.anchor, string.tip_x, string.tip_y) == (20, 20, 30)
    world.leave()
    assert world.view().string is None
    world.point(25, 30)
    world.hold(None)
    assert world.view().string is None


def test_picking_up_the_string_with_the_pointer_over_the_room_hangs_it_there():
    world = room("Mango")
    world.hold(Tool.BALL)
    world.point(20, 30)
    world.hold(Tool.STRING)
    assert world.view().string.anchor == 20


def test_the_string_tip_stays_inside_the_room():
    world = room("Mango")
    world.hold(Tool.STRING)
    world.point(20, -5)
    assert world.string.tip_y == 2
    world.point(20, 80)
    assert world.string.tip_y == FLOOR - 1


def test_a_playful_cat_climbs_up_to_bat_at_a_high_string():
    world = room("Mango", seed=0)
    playful(world)
    world.hold(Tool.STRING)
    world.point(20, 30)  # 9 pixels above the tree's middle platform
    leaps_up_there = []

    def watch(w):
        body = w.bodies["Mango"]
        if body.step is not None and body.step.doing is Doing.JUMP and body.step.hop is not None:
            leaps_up_there.append(body.surface)

    run(world, 20, watch)
    assert "tree_mid" in leaps_up_there
    assert Played("Mango", "string") in world.take_news()


def test_a_string_too_high_above_everything_is_ignored():
    world = room("Mango", width=120)
    playful(world)
    world.hold(Tool.STRING)
    world.point(100, 3)  # over bare floor, 54 pixels up
    run(world, 20)
    assert world.playing == {}
    assert world.take_news() == []


def test_putting_the_string_away_mid_game_ends_it_with_nothing_earned():
    world = room("Mango")
    mango = playful(world)
    world.hold(Tool.STRING)
    world.point(45, 40)
    run(world, 4)
    assert "Mango" in world.playing
    world.hold(None)
    run(world, 12)
    assert world.playing == {}
    assert Played("Mango", "string") not in world.take_news()
    assert mango.needs["play"] > 90


def test_resizing_rests_the_ball_on_the_new_floor_and_takes_the_string_down():
    world = room("Mango")
    world.hold(Tool.BALL)
    world.click(65, 20)
    world.hold(Tool.STRING)
    world.point(20, 30)
    world.fit(100, 80)
    assert (world.ball.y, world.string) == (79, None)
    world.fit(50, 54)
    assert world.ball.x <= 47.5


def test_an_hour_of_toys_never_gets_anyone_stuck():
    world = room("Mango", "Pebble", seed=4)
    rng = random.Random(9)
    world.hold(Tool.BALL)
    world.click(40, 20)
    last_change = {name: 0.0 for name in world.bodies}
    previous = {}
    sessions = 0
    t = 0.0
    for second in range(3600):
        if second % 600 == 0:
            world.set_mode(Mode.PLAY if second % 1200 else Mode.RELAX)
            world.feed()
        if second % 10 == 0:
            if rng.random() < 0.5:
                world.hold(Tool.STRING)
                world.point(rng.uniform(0, 70), rng.uniform(0, 57))
            else:
                world.hold(Tool.BALL)
                world.click(rng.uniform(0, 70), rng.uniform(0, 57))
        for _ in range(8):
            world.tick(TICK)
            t += TICK
            for name, body in world.bodies.items():
                state = (body.surface, round(body.x), body.step.doing if body.step else None)
                if state != previous.get(name):
                    previous[name], last_change[name] = state, t
                if body.step is None or body.step.doing is not Doing.JUMP:
                    assert body.y == world.scape.surface(body.surface).y
                assert 0 <= body.x <= 70
                assert t - last_change[name] <= 400  # the longest nap is 300 s
        sessions += sum(isinstance(e, Played) for e in world.take_news())
    assert sessions >= 10


def test_a_ball_left_lying_around_does_not_do_the_playing_for_you():
    world = room("Mango")
    world.set_mode(Mode.RELAX)
    world.hold(Tool.BALL)
    world.click(40, 20)
    world.hold(None)
    sessions = 0
    for _ in range(3 * 60):  # three hours, a minute at a time
        run(world, 60)
        sessions += sum(isinstance(e, Played) for e in world.take_news())
    assert sessions <= 2  # the drop, and perhaps a rebound
    assert world.cats[0].needs["play"] > 70  # so he still wants you to play with him


def test_the_string_tip_never_swings_out_of_the_room():
    world = room("Mango")
    world.hold(Tool.STRING)
    world.point(60, 30)
    world.point(0, 30)  # a fast sweep to the left wall
    tips = []
    run(world, 3, lambda w: tips.append(w.string.tip_x))
    assert min(tips) >= 0
    assert max(tips) <= 69
