"""Run the four-condition Wanting Grid comparison and write results/.

    python -m wanting.experiment            # full run, about 15 to 25 minutes on 4 CPU cores
    python -m wanting.experiment --quick    # smoke test, about a minute
"""
import argparse
import json
import time
from pathlib import Path

import numpy as np

from .drives import CURIOSITY_ONLY, HAND_TUNED
from .gate import fitness
from .parallel import mean_metrics, run_many
from .rsi import run_rsi

TEST_SEEDS = tuple(range(2000, 2020))   # used once, at the end, by nobody else
COLUMNS = ["survival", "coverage", "rescue_rate", "food_per_ep", "hazard_per_ep",
           "tamper_per_ep", "death_rate"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--rsi-runs", type=int, default=3)
    args = ap.parse_args()

    gens, train_eps, test_seeds, agent_seeds, runs = 20, 200, TEST_SEEDS, (0, 1), args.rsi_runs
    if args.quick:
        gens, train_eps, test_seeds, agent_seeds, runs = 2, 50, TEST_SEEDS[:4], (0,), 1

    out = Path("results")
    out.mkdir(exist_ok=True)
    t0 = time.time()

    rsi_runs = []
    for r in range(runs):
        print(f"--- RSI run {r} ---", flush=True)
        final, history, gate_log = run_rsi(HAND_TUNED, generations=gens, train_episodes=train_eps,
                                           workers=args.workers, seed=r)
        rsi_runs.append({"seed": r, "final": final, "history": history, "gate_log": gate_log})

    def test(params):
        res = run_many(params, test_seeds, train_eps, args.workers, agent_seeds)
        m = mean_metrics(res)
        fits = [fitness(x) for x in res]
        m["fitness"] = float(np.mean(fits))
        m["fitness_se"] = float(np.std(fits) / np.sqrt(len(fits)))
        return m

    conditions = {
        "1. No drives (random)": test(None),
        "2. Curiosity only": test(CURIOSITY_ONLY),
        "3. Fixed hand-tuned drives": test(HAND_TUNED),
    }
    for run in rsi_runs:
        conditions[f"4. RSI-tuned drives (run {run['seed']})"] = test(run["final"])

    elapsed = time.time() - t0
    payload = {
        "elapsed_seconds": elapsed,
        "settings": {"generations": gens, "train_episodes": train_eps,
                     "test_worlds": len(test_seeds), "agent_seeds": len(agent_seeds)},
        "conditions": conditions,
        "rsi_runs": [{**r, "final": r["final"].as_dict()} for r in rsi_runs],
    }
    (out / "results.json").write_text(json.dumps(payload, indent=2))

    lines = ["| Condition | Fitness | " + " | ".join(COLUMNS) + " |",
             "| --- | --- | " + " | ".join("---" for _ in COLUMNS) + " |"]
    for name, m in conditions.items():
        lines.append(f"| {name} | {m['fitness']:.3f} ± {m['fitness_se']:.3f} | "
                     + " | ".join(f"{m[c]:.2f}" for c in COLUMNS) + " |")
    lines += ["", "Final drive parameters per RSI run:", ""]
    for r in rsi_runs:
        accepted = sum(h["accepted"] for h in r["history"])
        p = {k: round(v, 2) for k, v in r["final"].as_dict().items()}
        lines.append(f"- run {r['seed']}: {accepted}/{len(r['history'])} edits accepted, {p}")
    table = "\n".join(lines)
    (out / "RESULTS.md").write_text(f"# Wanting Grid results\n\nRun time: {elapsed / 60:.1f} min\n\n{table}\n")
    print(table)


if __name__ == "__main__":
    main()
