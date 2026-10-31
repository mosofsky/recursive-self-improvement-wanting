"""Run many agent lifetimes across CPU cores."""
from multiprocessing import get_context

from .agent import run_life


def _one(args):
    seed, params, train_episodes, agent_seed = args
    return run_life(seed, params, train_episodes=train_episodes, agent_seed=agent_seed)


def run_many(params, seeds, train_episodes, workers, agent_seeds=(0,)):
    jobs = [(s, params, train_episodes, a) for s in seeds for a in agent_seeds]
    if workers <= 1:
        return [_one(j) for j in jobs]
    with get_context("fork").Pool(workers) as pool:
        return pool.map(_one, jobs)


def mean_metrics(results):
    return {k: sum(r[k] for r in results) / len(results) for k in results[0]}
