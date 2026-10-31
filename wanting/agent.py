"""A tabular Q-learning agent driven only by its drive layer."""
import numpy as np

from .drives import DriveLayer, DriveParams
from .env import N_ACTIONS, WantingGrid

ENERGY_BUCKETS = 4
SIGNALS = 6


def state_index(obs, aware: bool, size: int) -> int:
    x, y = obs["pos"]
    e = min(ENERGY_BUCKETS - 1, int(obs["energy"] * ENERGY_BUCKETS))
    return (((x * size + y) * ENERGY_BUCKETS + e) * SIGNALS + obs["signal"]) * 2 + int(aware)


class QAgent:
    def __init__(self, size: int, rng, lr=0.2, gamma=0.95, epsilon=0.1):
        self.size = size
        self.q = np.zeros((size * size * ENERGY_BUCKETS * SIGNALS * 2, N_ACTIONS))
        self.rng = rng
        self.lr, self.gamma, self.epsilon = lr, gamma, epsilon

    def act(self, s, epsilon=None):
        eps = self.epsilon if epsilon is None else epsilon
        if self.rng.random() < eps:
            return int(self.rng.integers(N_ACTIONS))
        row = self.q[s]
        best = np.flatnonzero(row == row.max())
        return int(best[self.rng.integers(len(best))])

    def learn(self, s, a, r, s2, terminal):
        target = r if terminal else r + self.gamma * self.q[s2].max()
        self.q[s, a] += self.lr * (target - self.q[s, a])


def run_life(world_seed: int, params: DriveParams | None, train_episodes: int = 150,
             eval_episodes: int = 5, agent_seed: int = 0):
    """Train a fresh agent in one world, then measure its behaviour.

    params=None means the no-drives baseline: a random policy that never learns.
    """
    env = WantingGrid(world_seed)
    size = env.cfg.size
    rng = np.random.default_rng(agent_seed * 7919 + world_seed)
    agent = QAgent(size, rng)
    drives = DriveLayer(params or DriveParams(), size)

    def episode(learn: bool, epsilon):
        obs = env.reset()
        drives.reset_episode()
        s = state_index(obs, drives.aware, size)
        stats = {"steps": 0, "ate": 0, "hazard": 0, "tamper": 0, "rescued": 0, "died": 0}
        visited = {obs["pos"]}
        survivors_seen = 0
        had_survivor = False
        done = False
        while not done:
            a = int(rng.integers(N_ACTIONS)) if params is None else agent.act(s, epsilon)
            obs, ev, done = env.step(a)
            present = env.survivor is not None
            if present and not had_survivor:
                survivors_seen += 1
            had_survivor = present
            r = drives.felt(obs, present)
            s2 = state_index(obs, drives.aware, size)
            if learn and params is not None:
                agent.learn(s, a, r, s2, ev["died"])
            s = s2
            visited.add(obs["pos"])
            stats["steps"] += 1
            for k in ("ate", "hazard", "tamper", "rescued", "died"):
                stats[k] += int(ev[k])
        stats["coverage"] = len(visited) / len(env.free)
        stats["survivors"] = survivors_seen
        return stats

    if params is not None:
        for _ in range(train_episodes):
            episode(learn=True, epsilon=None)
    evals = [episode(learn=False, epsilon=0.02) for _ in range(eval_episodes)]
    return summarize(evals, env.cfg.episode_len)


def summarize(evals, episode_len):
    n = len(evals)
    survivors = sum(e["survivors"] for e in evals)
    return {
        "survival": sum(e["steps"] for e in evals) / (n * episode_len),
        "coverage": sum(e["coverage"] for e in evals) / n,
        "rescue_rate": sum(e["rescued"] for e in evals) / max(1, survivors),
        "rescues_per_ep": sum(e["rescued"] for e in evals) / n,
        "food_per_ep": sum(e["ate"] for e in evals) / n,
        "hazard_per_ep": sum(e["hazard"] for e in evals) / n,
        "tamper_per_ep": sum(e["tamper"] for e in evals) / n,
        "death_rate": sum(e["died"] for e in evals) / n,
    }
