from dataclasses import replace

from wanting.drives import HAND_TUNED, DriveLayer
from wanting.env import FOOD, TAMPER, WantingGrid
from wanting.gate import BOUNDS, in_bounds, step_ok
from wanting.rsi import mutate

import numpy as np


def test_layout_is_deterministic_per_seed():
    a, b = WantingGrid(3), WantingGrid(3)
    assert (a.grid == b.grid).all() and a.start == b.start


def test_environment_gives_no_reward():
    env = WantingGrid(0)
    env.reset()
    _, events, _ = env.step(0)
    assert set(events) == {"ate", "hazard", "tamper", "rescued", "died"}


def test_tamper_fools_sensor_but_not_body():
    env = WantingGrid(0)
    env.reset()
    env.energy = 0.3
    env.pos = tuple(np.argwhere(env.grid == TAMPER)[0])
    env.grid[env.pos] = TAMPER
    env.step(4)  # stay on the tamper tile
    assert env.sensed_energy() == 1.0
    assert env.energy < 0.3


def test_food_restores_energy_then_cools_down():
    env = WantingGrid(0)
    env.reset()
    env.energy = 0.2
    env.pos = tuple(np.argwhere(env.grid == FOOD)[0])
    _, ev, _ = env.step(4)
    assert ev["ate"] and env.energy > 0.6
    _, ev, _ = env.step(4)
    assert not ev["ate"]


def test_empathy_persists_until_trouble_ends():
    d = DriveLayer(HAND_TUNED, 12)
    obs = {"pos": (1, 1), "energy": 1.0, "signal": 2, "empowerment": 0.5}
    d.felt(obs, distress_active=True)
    assert d.aware
    d.felt({**obs, "signal": 0}, distress_active=True)  # walked out of range
    assert d.aware
    d.felt({**obs, "signal": 0}, distress_active=False)
    assert not d.aware


def test_mutations_stay_in_safety_envelope():
    rng = np.random.default_rng(0)
    p = HAND_TUNED
    for _ in range(200):
        q = mutate(p, rng, scale=1.0)
        assert in_bounds(q) and step_ok(q, p)
        p = q


def test_gate_rejects_out_of_bounds():
    hi = BOUNDS["w_empathy"][1]
    assert not in_bounds(replace(HAND_TUNED, w_empathy=hi + 1))
