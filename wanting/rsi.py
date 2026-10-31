"""The recursive self-improvement loop over the drive layer.

Each generation the loop proposes mutated drive parameters, trains fresh agents
with them on training worlds, and sends its best proposal to the gate. Only the
gate decides what becomes the new incumbent.
"""
from dataclasses import fields, replace

import numpy as np

from .drives import DriveParams
from .gate import BOUNDS, MAX_STEP, Gate, fitness
from .parallel import mean_metrics, run_many

TRAIN_SEEDS = tuple(range(0, 6))


def mutate(p: DriveParams, rng, scale=0.12):
    changes = {}
    for f in fields(p):
        lo, hi = BOUNDS[f.name]
        step = np.clip(rng.normal(0, scale), -MAX_STEP, MAX_STEP) * (hi - lo)
        changes[f.name] = float(np.clip(getattr(p, f.name) + step, lo, hi))
    return replace(p, **changes)


def run_rsi(start: DriveParams, generations=20, proposals=6, train_episodes=200,
            workers=4, seed=0, verbose=True):
    rng = np.random.default_rng(seed)
    gate = Gate(start, train_episodes, workers)
    incumbent = start
    inc_train = fitness(mean_metrics(run_many(incumbent, TRAIN_SEEDS, train_episodes, workers)))
    history = []
    for g in range(generations):
        scored = []
        for _ in range(proposals):
            cand = mutate(incumbent, rng)
            m = mean_metrics(run_many(cand, TRAIN_SEEDS, train_episodes, workers))
            scored.append((fitness(m), cand))
        best_fit, best = max(scored, key=lambda t: t[0])
        if best_fit <= inc_train:
            accepted, reason = False, "no training improvement"
        else:
            accepted, reason = gate.review(best)
        if accepted:
            incumbent, inc_train = best, best_fit
        history.append({"generation": g, "train_fitness": inc_train, "proposal_fitness": best_fit,
                        "accepted": accepted, "reason": reason, "incumbent": incumbent.as_dict()})
        if verbose:
            print(f"gen {g:2d} proposal {best_fit:.3f} incumbent {inc_train:.3f} "
                  f"{'ACCEPT' if accepted else 'reject'} ({reason})", flush=True)
    return incumbent, history, gate.log
