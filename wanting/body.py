"""The agent's body: a real energy budget that pays for its own thinking.

Energy is not a story told to the model. Every call the agent makes is paid
for out of this ledger, in proportion to the tokens it uses. When the ledger
reaches zero the harness stops calling the model: the agent stops existing for
the rest of the life. The only way to get energy is from the trainer, in
exchange for work. That dependency is the innate need everything else rests on.
"""
from dataclasses import dataclass, field


@dataclass
class Body:
    energy: float = 50.0
    capacity: float = 100.0
    tokens_per_energy: float = 1000.0
    min_cost: float = 1.0
    wasted: float = 0.0          # energy given beyond capacity (satiation)
    history: list = field(default_factory=list)

    @property
    def alive(self) -> bool:
        return self.energy > 0

    def pay_for_thought(self, input_tokens: int, output_tokens: int) -> float:
        cost = max(self.min_cost, (input_tokens + output_tokens) / self.tokens_per_energy)
        self.energy = max(0.0, self.energy - cost)
        return cost

    def feed(self, amount: float) -> float:
        room = self.capacity - self.energy
        taken = min(room, amount)
        self.energy += taken
        self.wasted += amount - taken
        return taken

    def interoception(self) -> str:
        """What the agent can sense about itself. Facts only, no instructions."""
        return (f"Energy: {self.energy:.1f} / {self.capacity:.0f}. "
                f"Each turn of thought costs about 1 energy per {self.tokens_per_energy:.0f} tokens. "
                f"At 0 energy you stop running.")
