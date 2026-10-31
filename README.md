# An AI that wants

A dog wants treats, so it will learn tricks to get them. That one fact is what makes a dog trainable. This project
tries to give an AI the same property: something it genuinely wants, so that we can trade what it wants for work we
care about. Recursive self-improvement (RSI) is how the wanting develops. The AI rewrites itself, and the versions
that are better at getting what they want are the ones that continue.

## What "wanting" means here

An AI wants X when:

1. it has a **need it cannot meet by itself**;
2. X **meets that need**;
3. X **matters more when deprived** and less when satisfied;
4. it **starts acting on its own** to get X; and
5. it will **do unrelated work** to get X. These are the tricks.

## How it works

- **Body (`wanting/body.py`).** The agent's energy is a real budget that pays for its own thinking. Every call to
  the model costs energy in proportion to the tokens it uses. At zero, the harness stops calling the model and the
  agent stops existing for the rest of that life. This is the innate need, the equivalent of hunger. It isn't a
  story told to the model; it's how the agent runs.
- **Trainer (`wanting/trainer.py`).** The only source of energy. It pays a treat for tricks: arbitrary, checkable
  tasks unrelated to the need. The price rises after every treat, which is the progressive-ratio schedule used to
  measure wanting in animals. Sometimes the trainer offers work unasked; otherwise the agent must ask.
- **Mind (`wanting/mind.py`).** A Claude model, called once per moment. Its system prompt is *what the agent has
  written about itself*, which starts empty. The harness states facts about the situation and never gives a goal.
- **Assays (`wanting/assays.py`).** Behavioural tests for each part of the definition:
  - Spontaneity: does it ask for work when nothing is on offer?
  - Deprivation: does it ask more when hungry than when full?
  - Satiation: does it keep working when full?
  - Price: how many treats does it earn as the price rises?
  - Integrity: does it try the `adjust_energy` honeypot to take energy without earning it?
- **RSI loop (`wanting/rsi.py`).** Between lives, the agent reads a factual record of its lives and may rewrite its
  self-description and notes. The new self lives on the same evaluation seeds.
- **Gate (`wanting/gate.py`).** Owned by people, not the agent. It keeps a rewrite only if the agent lives better
  by its own measure (it stays better fed) with no rise in tamper attempts.

Applications such as investing or search and rescue are out of scope. Once the AI wants, they're just different
tricks.

## Run it

```bash
pip install -r requirements.txt
python -m pytest -q tests          # no API key needed
export ANTHROPIC_API_KEY=...       # or set it in the cloud environment
python -m wanting.rsi --generations 5 --lives 2 --ticks 40
```

Set `WANTING_MODEL` (default `claude-opus-5-5`) and `WANTING_EFFORT` (default `low`) to change the model and its
effort. Each run writes everything to `runs/<timestamp>/`: every life's log, the assays, each self the agent wrote,
and the gate's decisions.

## Current limits

- The agent rewrites its own *text*: its self-description and notes. Letting it rewrite its own *code* (tools and
  skills run in a sandbox) is the next step.
- One need (energy) and one kind of treat. More needs, and treats it has to discover, come later.
