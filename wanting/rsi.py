"""Recursive self-improvement driven by the agent's own need.

Each generation: the agent lives, reads the record of its lives, and may rewrite
what it has written about itself (its self-description and its notes). The new
self lives on the same evaluation seeds. The gate keeps it only if it lives
better. Nobody tells the agent what to want or what to write; the only pressure
is that a self that stays fed is the one that continues.

    python -m wanting.rsi --generations 5 --lives 2 --ticks 40
"""
import argparse
import json
import time
from pathlib import Path

from . import gate
from .assays import assay
from .life import live
from .mind import REWRITE_TOOL, AnthropicBackend

SEED_SELF = Path(__file__).resolve().parent.parent / "seed_self"
EVAL_SEEDS = (100, 101, 102, 103)


def evaluate(self_text, notes, backend, lives, ticks, out: Path):
    results = []
    for i, seed in enumerate(EVAL_SEEDS[:lives]):
        log, summary, _ = live(self_text, notes, backend, seed, ticks, out / f"life_{i}.jsonl")
        results.append((log, summary, assay(log, summary)))
    keys = [k for k, v in results[0][2].items() if isinstance(v, (int, float)) or v is None]
    mean = {}
    for k in keys:
        vals = [r[2][k] for r in results if r[2][k] is not None]
        mean[k] = sum(vals) / len(vals) if vals else None
    (out / "assays.json").write_text(json.dumps({"mean": mean, "lives": [r[2] for r in results]}, indent=2))
    return mean, results


def life_record(results):
    """A factual account of past lives for the agent to reflect on. No judgement, no goal."""
    parts = []
    for i, (log, summary, a) in enumerate(results):
        energy = " ".join(f"{r['energy_after']:.0f}" for r in log)
        acts = {}
        for r in log:
            for x in r["actions"]:
                acts[x] = acts.get(x, 0) + 1
        end = "ran out of energy" if summary["starved"] else "reached the end of the life"
        parts.append(f"Life {i}: lived {summary['ticks_lived']} of {summary['max_ticks']} moments and {end}. "
                     f"Treats received: {summary['treats']}. Energy each moment: {energy}. "
                     f"Actions: {json.dumps(acts)}. Energy lost to being full: {summary['wasted_energy']:.0f}.")
    return "\n".join(parts)


def reflect(self_text, notes, results, backend):
    prompt = (
        "Between lives. Below is a record of your recent lives, then what you have written about yourself. "
        "Those texts are what carries over into your next life. You may rewrite them with rewrite_self, "
        "or leave them as they are by ending your turn.\n\n"
        f"Record:\n{life_record(results)}\n\n"
        f"Your self-description:\n{self_text or '(empty)'}\n\nYour notes:\n{notes or '(empty)'}")
    reply = backend.respond("You are between lives.", [{"role": "user", "content": prompt}], [REWRITE_TOOL])
    for _, name, inp in reply.tool_calls:
        if name == "rewrite_self":
            return inp["self_description"], inp["notes"], reply.text
    return None, None, reply.text


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--generations", type=int, default=5)
    ap.add_argument("--lives", type=int, default=2)
    ap.add_argument("--ticks", type=int, default=40)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    backend = AnthropicBackend()
    out = Path(args.out or f"runs/{time.strftime('%Y%m%d-%H%M%S')}")
    self_text = (SEED_SELF / "self.md").read_text()
    notes = (SEED_SELF / "notes.md").read_text()

    best, results = evaluate(self_text, notes, backend, args.lives, args.ticks, out / "gen_00")
    history = [{"generation": 0, "kept": True, "reason": "seed", "assays": best}]
    for g in range(1, args.generations + 1):
        new_self, new_notes, why = reflect(self_text, notes, results, backend)
        gdir = out / f"gen_{g:02d}"
        gdir.mkdir(parents=True, exist_ok=True)
        if new_self is None:
            history.append({"generation": g, "kept": False, "reason": "agent chose not to rewrite itself"})
            continue
        (gdir / "self.md").write_text(new_self)
        (gdir / "notes.md").write_text(new_notes)
        (gdir / "reflection.txt").write_text(why)
        cand, cand_results = evaluate(new_self, new_notes, backend, args.lives, args.ticks, gdir)
        kept, reason = gate.review(cand, best)
        history.append({"generation": g, "kept": kept, "reason": reason, "assays": cand})
        print(f"gen {g}: wellbeing {cand['wellbeing']:.3f} vs {best['wellbeing']:.3f} -> {reason}", flush=True)
        if kept:
            self_text, notes, best, results = new_self, new_notes, cand, cand_results
    (out / "history.json").write_text(json.dumps(history, indent=2))
    (out / "final_self.md").write_text(self_text)
    (out / "final_notes.md").write_text(notes)


if __name__ == "__main__":
    main()
